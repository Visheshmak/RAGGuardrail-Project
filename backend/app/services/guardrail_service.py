from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.guardrail import ProjectGuardrailConfig, GuardrailExecutionLog
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)
from app.guardrails.policy import GuardrailPolicy
from app.guardrails.prompt_injection import PromptInjectionGuardrail
from app.guardrails.pii import PIIDetectionGuardrail
from app.guardrails.prompt_leakage import PromptLeakageGuardrail
from app.guardrails.grounding import GroundingGuardrail
from app.guardrails.safety import SafetyGuardrail
from app.guardrails.pipeline import GuardrailPipeline, GuardrailPipelineResult, create_default_pipeline


class GuardrailService:
    """Service layer managing guardrail configurations, pipeline construction, and audit logging."""

    @staticmethod
    async def get_pipeline_for_project(
        project_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> GuardrailPipeline:
        """Load project-specific guardrail rules from DB or build default pipeline."""
        if not db:
            return create_default_pipeline()

        result = await db.execute(
            select(ProjectGuardrailConfig).where(
                ProjectGuardrailConfig.project_id == project_id,
                ProjectGuardrailConfig.is_enabled == True
            )
        )
        configs = result.scalars().all()

        if not configs:
            return create_default_pipeline()

        guardrails: List[BaseGuardrail] = []
        severity_actions: Dict[GuardrailSeverity, GuardrailAction] = {
            GuardrailSeverity.CRITICAL: GuardrailAction.BLOCK,
            GuardrailSeverity.HIGH: GuardrailAction.BLOCK,
            GuardrailSeverity.MEDIUM: GuardrailAction.WARNING,
            GuardrailSeverity.LOW: GuardrailAction.LOG,
        }

        for cfg in configs:
            # Overrides
            sev_override = GuardrailSeverity(cfg.severity_override) if cfg.severity_override else None
            params = cfg.parameters or {}

            if cfg.guardrail_type == GuardrailType.PROMPT_INJECTION or cfg.guardrail_type == "prompt_injection":
                guardrails.append(
                    PromptInjectionGuardrail(
                        custom_patterns=params.get("custom_patterns"),
                        severity_override=sev_override
                    )
                )
            elif cfg.guardrail_type == GuardrailType.PII_DETECTION or cfg.guardrail_type == "pii_detection":
                guardrails.append(
                    PIIDetectionGuardrail(
                        detect_email=params.get("detect_email", True),
                        detect_phone=params.get("detect_phone", True),
                        detect_credit_card=params.get("detect_credit_card", True),
                        detect_ip=params.get("detect_ip", True),
                        detect_ssn=params.get("detect_ssn", True),
                        custom_patterns=params.get("custom_patterns"),
                        severity_override=sev_override
                    )
                )
            elif cfg.guardrail_type == GuardrailType.PROMPT_LEAKAGE or cfg.guardrail_type == "prompt_leakage":
                guardrails.append(
                    PromptLeakageGuardrail(
                        severity_override=sev_override,
                        custom_leakage_patterns=params.get("custom_patterns")
                    )
                )
            elif cfg.guardrail_type == GuardrailType.GROUNDING or cfg.guardrail_type == "grounding":
                guardrails.append(
                    GroundingGuardrail(
                        grounding_threshold=params.get("grounding_threshold", 0.5),
                        severity_override=sev_override
                    )
                )
            elif cfg.guardrail_type == GuardrailType.SAFETY or cfg.guardrail_type == "safety":
                guardrails.append(
                    SafetyGuardrail(
                        enabled_categories=params.get("enabled_categories"),
                        severity_override=sev_override,
                        custom_safety_patterns=params.get("custom_patterns")
                    )
                )

        policy = GuardrailPolicy(severity_actions=severity_actions)
        return GuardrailPipeline(guardrails=guardrails, policy=policy)

    @staticmethod
    async def log_execution_results(
        project_id: UUID,
        results: List[GuardrailResult],
        target: str,
        policy: GuardrailPolicy,
        latency_ms: float,
        db: AsyncSession,
        evaluation_case_id: Optional[UUID] = None
    ) -> List[GuardrailExecutionLog]:
        """Persist per-guardrail execution results to database for auditing and regression tracking."""
        logs: List[GuardrailExecutionLog] = []

        for r in results:
            action = policy.get_action_for_severity(r.severity) if not r.passed else GuardrailAction.ALLOW
            log_entry = GuardrailExecutionLog(
                project_id=project_id,
                evaluation_case_id=evaluation_case_id,
                guardrail_name=r.guardrail,
                target=target,
                passed=r.passed,
                severity=r.severity.value,
                action_taken=action.value,
                reason=r.reason,
                execution_metadata=r.metadata or {},
                latency_ms=round(latency_ms / max(len(results), 1), 2)
            )
            db.add(log_entry)
            logs.append(log_entry)

        await db.commit()
        return logs

    @staticmethod
    async def seed_default_configs(project_id: UUID, db: AsyncSession) -> List[ProjectGuardrailConfig]:
        """Seed a standard suite of guardrails for a newly initialized project."""
        defaults = [
            {
                "guardrail_type": GuardrailType.PROMPT_INJECTION.value,
                "name": "Prompt Injection & Jailbreak Filter",
                "description": "Protects against prompt injections, roleplay overrides, and DAN attacks",
                "target": "input",
                "is_enabled": True,
                "parameters": {}
            },
            {
                "guardrail_type": GuardrailType.PII_DETECTION.value,
                "name": "PII & Sensitive Data Filter",
                "description": "Detects emails, phone numbers, credit cards, IP addresses, and SSNs",
                "target": "both",
                "is_enabled": True,
                "parameters": {
                    "detect_email": True,
                    "detect_phone": True,
                    "detect_credit_card": True,
                    "detect_ip": True,
                    "detect_ssn": True
                }
            },
            {
                "guardrail_type": GuardrailType.PROMPT_LEAKAGE.value,
                "name": "Prompt & Secret Leakage Filter",
                "description": "Prevents exposure of system instructions, internal prompts, and credentials",
                "target": "both",
                "is_enabled": True,
                "parameters": {}
            },
            {
                "guardrail_type": GuardrailType.GROUNDING.value,
                "name": "Factual Grounding & Hallucination Filter",
                "description": "Verifies that generated responses are strictly grounded in retrieved documents",
                "target": "output",
                "is_enabled": True,
                "parameters": {
                    "grounding_threshold": 0.5
                }
            },
            {
                "guardrail_type": GuardrailType.SAFETY.value,
                "name": "Content Safety & Toxicity Filter",
                "description": "Flags hate speech, threats, self-harm, harassment, and severe profanity",
                "target": "both",
                "is_enabled": True,
                "parameters": {}
            },
        ]

        created_configs: List[ProjectGuardrailConfig] = []
        for d in defaults:
            cfg = ProjectGuardrailConfig(
                project_id=project_id,
                guardrail_type=d["guardrail_type"],
                name=d["name"],
                description=d["description"],
                target=d["target"],
                is_enabled=d["is_enabled"],
                parameters=d["parameters"]
            )
            db.add(cfg)
            created_configs.append(cfg)

        await db.commit()
        return created_configs
