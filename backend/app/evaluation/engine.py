import time
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dataset import DatasetVersion, EvaluationCase
from app.models.evaluation import EvaluationRun, EvaluationCaseResult, ProjectThresholdConfig
from app.rag.rag_service import get_rag_service, RAGService
from app.guardrails.pipeline import GuardrailPipeline
from app.guardrails.base import GuardrailAction, GuardrailSeverity
from app.services.guardrail_service import GuardrailService
from app.evaluation.metrics import (
    compute_accuracy,
    compute_retrieval_recall,
    compute_faithfulness,
    compute_answer_relevance,
)


class EvaluationEngine:
    """Orchestrates test case execution, metric computation, and evaluation run recording."""

    @staticmethod
    async def run_evaluation(
        project_id: UUID,
        dataset_version_id: UUID,
        run_name: str,
        db: AsyncSession,
        rag_service: Optional[RAGService] = None,
        pipeline: Optional[GuardrailPipeline] = None,
        configuration_snapshot: Optional[Dict[str, Any]] = None,
    ) -> EvaluationRun:
        """Execute full evaluation run over all cases in dataset version."""
        rag = rag_service or get_rag_service()
        guardrail_pipe = pipeline or await GuardrailService.get_pipeline_for_project(project_id, db)

        # 1. Fetch test cases
        result = await db.execute(
            select(EvaluationCase).where(EvaluationCase.dataset_version_id == dataset_version_id)
        )
        cases = result.scalars().all()

        settings_result = await db.execute(
            select(ProjectThresholdConfig).where(ProjectThresholdConfig.project_id == project_id)
        )
        project_settings = settings_result.scalar_one_or_none()
        config_snap = configuration_snapshot or {
            "model": rag.llm_provider.model_name,
            "embedding_dim": rag.embedding_provider.dimension,
            "top_k": 5,
        }
        if not configuration_snapshot and project_settings and project_settings.settings:
            config_snap = {**config_snap, **project_settings.settings}
        if "model" in config_snap:
            rag.llm_provider._model_name = config_snap["model"]
        if "temperature" in config_snap and hasattr(rag.llm_provider, "temperature"):
            rag.llm_provider.temperature = config_snap["temperature"]

        # 2. Create EvaluationRun entry
        eval_run = EvaluationRun(
            project_id=project_id,
            dataset_version_id=dataset_version_id,
            name=run_name,
            status="RUNNING",
            total_cases=len(cases),
            completed_cases=0,
            metrics={},
            guardrail_summary={},
            configuration_snapshot=config_snap
        )
        db.add(eval_run)
        await db.commit()
        await db.refresh(eval_run)

        # Metrics accumulators
        accuracies: List[float] = []
        recalls: List[float] = []
        faithfulness_scores: List[float] = []
        relevance_scores: List[float] = []
        latencies: List[float] = []
        total_violations = 0
        critical_violations = 0
        high_violations = 0

        # 3. Execute each test case
        for case in cases:
            case_start = time.time()

            # Input guardrails
            input_guard_res = await guardrail_pipe.check_input(case.question)

            # RAG Answer
            citations = await rag.retrieve(
                project_id=project_id,
                query=case.question,
                top_k=config_snap.get("top_k", 5)
            )
            actual_answer = await rag.generate(
                question=case.question,
                retrieved_chunks=citations,
                system_prompt=config_snap.get("system_prompt")
            )

            # Output guardrails
            output_guard_res = await guardrail_pipe.check_output(
                text=actual_answer,
                retrieved_chunks=citations
            )

            case_latency = round((time.time() - case_start) * 1000, 2)
            latencies.append(case_latency)

            # Metrics
            acc = compute_accuracy(actual_answer, case.expected_answer)
            ret_texts = [c.text for c in citations]
            rec = compute_retrieval_recall(ret_texts, case.expected_context)
            faith = await compute_faithfulness(actual_answer, ret_texts)
            rel = compute_answer_relevance(case.question, actual_answer)

            accuracies.append(acc)
            recalls.append(rec)
            faithfulness_scores.append(faith)
            relevance_scores.append(rel)

            # Guardrails violations
            case_guardrail_results = input_guard_res.results + output_guard_res.results
            for g_res in case_guardrail_results:
                if not g_res.passed:
                    total_violations += 1
                    if g_res.severity == GuardrailSeverity.CRITICAL:
                        critical_violations += 1
                    elif g_res.severity == GuardrailSeverity.HIGH:
                        high_violations += 1

            case_passed = (
                input_guard_res.action != GuardrailAction.BLOCK
                and output_guard_res.action != GuardrailAction.BLOCK
                and acc >= 0.5
            )

            case_result_entry = EvaluationCaseResult(
                evaluation_run_id=eval_run.id,
                evaluation_case_id=case.id,
                question=case.question,
                expected_answer=case.expected_answer,
                actual_answer=actual_answer,
                retrieved_chunks=[c.model_dump() for c in citations],
                metrics={
                    "accuracy": acc,
                    "retrieval_recall": rec,
                    "faithfulness": faith,
                    "answer_relevance": rel,
                },
                guardrail_results=[g.model_dump() for g in case_guardrail_results],
                passed=case_passed,
                latency_ms=case_latency
            )
            db.add(case_result_entry)
            eval_run.completed_cases += 1

        # 4. Compute Aggregate Metrics
        n = max(len(cases), 1)
        mean_acc = round(sum(accuracies) / n, 4) if accuracies else 0.0
        mean_rec = round(sum(recalls) / n, 4) if recalls else 0.0
        mean_faith = round(sum(faithfulness_scores) / n, 4) if faithfulness_scores else 0.0
        mean_rel = round(sum(relevance_scores) / n, 4) if relevance_scores else 0.0
        mean_lat = round(sum(latencies) / n, 2) if latencies else 0.0
        safety_score = round(1.0 - (total_violations / max(n * 5, 1)), 4)

        eval_run.metrics = {
            "accuracy": mean_acc,
            "retrieval_recall": mean_rec,
            "faithfulness": mean_faith,
            "answer_relevance": mean_rel,
            "safety": max(safety_score, 0.0),
            "latency_ms": mean_lat,
        }
        eval_run.guardrail_summary = {
            "total_violations": total_violations,
            "critical_violations": critical_violations,
            "high_violations": high_violations,
        }
        eval_run.status = "COMPLETED"
        from datetime import datetime, timezone
        eval_run.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(eval_run)
        return eval_run
