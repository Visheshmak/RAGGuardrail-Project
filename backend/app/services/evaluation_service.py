from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.evaluation import (
    EvaluationRun,
    Baseline,
    RegressionResult,
    ProjectThresholdConfig,
)
from app.evaluation.regression import RegressionEngine, ReleaseDecision, DEFAULT_THRESHOLDS


class EvaluationService:
    """Service managing evaluation runs, baselines, regression comparisons, and release gating."""

    @staticmethod
    async def get_or_create_threshold_config(
        project_id: UUID,
        db: AsyncSession
    ) -> ProjectThresholdConfig:
        """Fetch project threshold config or initialize with defaults."""
        result = await db.execute(
            select(ProjectThresholdConfig).where(ProjectThresholdConfig.project_id == project_id)
        )
        cfg = result.scalar_one_or_none()
        if not cfg:
            cfg = ProjectThresholdConfig(
                project_id=project_id,
                thresholds=DEFAULT_THRESHOLDS,
                settings={},
                block_on_critical_guardrail=True
            )
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
        return cfg

    @staticmethod
    async def set_active_baseline(
        project_id: UUID,
        evaluation_run_id: UUID,
        notes: Optional[str],
        db: AsyncSession
    ) -> Baseline:
        """Promote an evaluation run to be the project's active baseline (deactivating any prior baseline)."""
        # 1. Fetch evaluation run
        eval_result = await db.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == evaluation_run_id,
                EvaluationRun.project_id == project_id
            )
        )
        eval_run = eval_result.scalar_one_or_none()
        if not eval_run:
            raise ValueError("Evaluation run not found for this project")

        # 2. Deactivate existing active baselines
        await db.execute(
            update(Baseline)
            .where(Baseline.project_id == project_id, Baseline.is_active == True)
            .values(is_active=False)
        )

        # 3. Determine next version number
        version_result = await db.execute(
            select(Baseline.version)
            .where(Baseline.project_id == project_id)
            .order_by(Baseline.version.desc())
        )
        highest_version = version_result.scalars().first() or 0
        new_version = highest_version + 1

        # 4. Create new baseline
        baseline = Baseline(
            project_id=project_id,
            evaluation_run_id=evaluation_run_id,
            version=new_version,
            is_active=True,
            configuration_snapshot=eval_run.configuration_snapshot or {},
            metrics_snapshot=eval_run.metrics or {},
            notes=notes
        )
        db.add(baseline)
        await db.commit()
        await db.refresh(baseline)
        return baseline

    @staticmethod
    async def get_active_baseline(
        project_id: UUID,
        db: AsyncSession
    ) -> Optional[Baseline]:
        """Fetch the current active baseline for a project."""
        result = await db.execute(
            select(Baseline).where(
                Baseline.project_id == project_id,
                Baseline.is_active == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def compare_run_against_baseline(
        project_id: UUID,
        evaluation_run_id: UUID,
        baseline_id: Optional[UUID],
        db: AsyncSession
    ) -> Tuple[ReleaseDecision, List[RegressionResult]]:
        """Compare evaluation run metrics against baseline and persist regression results."""
        # 1. Fetch evaluation run
        run_res = await db.execute(
            select(EvaluationRun).where(
                EvaluationRun.id == evaluation_run_id,
                EvaluationRun.project_id == project_id
            )
        )
        eval_run = run_res.scalar_one_or_none()
        if not eval_run:
            raise ValueError("Evaluation run not found")

        # 2. Fetch baseline
        if baseline_id:
            base_res = await db.execute(
                select(Baseline).where(Baseline.id == baseline_id, Baseline.project_id == project_id)
            )
            baseline = base_res.scalar_one_or_none()
        else:
            baseline = await EvaluationService.get_active_baseline(project_id, db)

        if not baseline:
            raise ValueError("No baseline found for comparison")

        # 3. Fetch project threshold config
        threshold_cfg = await EvaluationService.get_or_create_threshold_config(project_id, db)

        # 4. Run comparison engine
        decision = RegressionEngine.compare(
            current_metrics=eval_run.metrics,
            baseline_metrics=baseline.metrics_snapshot,
            threshold_config=threshold_cfg.thresholds,
            guardrail_summary=eval_run.guardrail_summary,
            block_on_critical_guardrail=threshold_cfg.block_on_critical_guardrail
        )
        decision.baseline_version = baseline.version
        decision.evaluation_run_id = str(eval_run.id)

        # 5. Persist regression results
        # Clean up existing results for this run first
        existing_reg_res = await db.execute(
            select(RegressionResult).where(RegressionResult.evaluation_run_id == evaluation_run_id)
        )
        for old in existing_reg_res.scalars().all():
            await db.delete(old)

        created_results: List[RegressionResult] = []
        for detail in decision.metrics_comparison:
            baseline_score = detail.baseline
            current_score = detail.current
            abs_diff = round(current_score - baseline_score, 4)
            rel_diff = round(abs_diff / baseline_score, 4) if baseline_score != 0 else 0.0

            reg_entry = RegressionResult(
                evaluation_run_id=eval_run.id,
                baseline_id=baseline.id,
                metric=detail.metric,
                baseline_score=baseline_score,
                current_score=current_score,
                absolute_difference=abs_diff,
                relative_difference=rel_diff,
                allowed_regression=detail.allowed_regression,
                status=detail.status
            )
            db.add(reg_entry)
            created_results.append(reg_entry)

        await db.commit()
        return decision, created_results
