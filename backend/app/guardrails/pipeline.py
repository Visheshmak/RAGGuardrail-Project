import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.guardrails.base import (
    BaseGuardrail,
    GuardrailAction,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
)
from app.guardrails.policy import GuardrailPolicy
from app.guardrails.prompt_injection import PromptInjectionGuardrail
from app.guardrails.pii import PIIDetectionGuardrail
from app.guardrails.prompt_leakage import PromptLeakageGuardrail
from app.guardrails.grounding import GroundingGuardrail
from app.guardrails.safety import SafetyGuardrail


class GuardrailPipelineResult(BaseModel):
    passed: bool = Field(..., description="Overall pass status (True if no blocking violations)")
    action: GuardrailAction = Field(..., description="Overall action to take: ALLOW, LOG, WARNING, BLOCK")
    blocked_reason: Optional[str] = Field(None, description="Detailed explanation if request was blocked")
    max_severity: Optional[GuardrailSeverity] = Field(None, description="Maximum violation severity encountered")
    results: List[GuardrailResult] = Field(default_factory=list, description="Per-guardrail results")
    latency_ms: float = Field(0.0, description="Execution time in milliseconds")
    target: GuardrailTarget = Field(GuardrailTarget.BOTH, description="Target phase of evaluation")


class GuardrailPipeline:
    """Modular orchestration pipeline for running input and output guardrails."""

    def __init__(
        self,
        guardrails: Optional[List[BaseGuardrail]] = None,
        policy: Optional[GuardrailPolicy] = None,
    ):
        self.policy = policy or GuardrailPolicy()
        if guardrails is not None:
            self.guardrails = guardrails
        else:
            # Default guardrails suite
            self.guardrails = [
                PromptInjectionGuardrail(),
                PIIDetectionGuardrail(),
                PromptLeakageGuardrail(),
                GroundingGuardrail(),
                SafetyGuardrail(),
            ]

    def add_guardrail(self, guardrail: BaseGuardrail) -> "GuardrailPipeline":
        self.guardrails.append(guardrail)
        return self

    async def check_input(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailPipelineResult:
        """Run all input-targeted guardrails on user queries or prompts."""
        start_time = time.time()
        applicable = [
            g for g in self.guardrails
            if g.target in (GuardrailTarget.INPUT, GuardrailTarget.BOTH)
        ]

        results: List[GuardrailResult] = []
        ctx = context or {}
        ctx["is_output"] = False

        for g in applicable:
            res = await g.check(text, context=ctx)
            results.append(res)

        action, blocked_reason, max_sev = self.policy.evaluate_results(results)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return GuardrailPipelineResult(
            passed=(action != GuardrailAction.BLOCK),
            action=action,
            blocked_reason=blocked_reason,
            max_severity=max_sev,
            results=results,
            latency_ms=elapsed_ms,
            target=GuardrailTarget.INPUT,
        )

    async def check_output(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        retrieved_chunks: Optional[List[Any]] = None
    ) -> GuardrailPipelineResult:
        """Run all output-targeted guardrails on generated LLM responses."""
        start_time = time.time()
        applicable = [
            g for g in self.guardrails
            if g.target in (GuardrailTarget.OUTPUT, GuardrailTarget.BOTH)
        ]

        results: List[GuardrailResult] = []
        ctx = context or {}
        ctx["is_output"] = True
        if retrieved_chunks is not None:
            ctx["retrieved_chunks"] = retrieved_chunks

        for g in applicable:
            res = await g.check(text, context=ctx)
            results.append(res)

        action, blocked_reason, max_sev = self.policy.evaluate_results(results)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return GuardrailPipelineResult(
            passed=(action != GuardrailAction.BLOCK),
            action=action,
            blocked_reason=blocked_reason,
            max_severity=max_sev,
            results=results,
            latency_ms=elapsed_ms,
            target=GuardrailTarget.OUTPUT,
        )

    async def check_interaction(
        self,
        question: str,
        answer: str,
        retrieved_chunks: Optional[List[Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailPipelineResult:
        """Evaluate both input prompt and output response in a complete RAG interaction."""
        start_time = time.time()
        
        # Check input
        input_res = await self.check_input(question, context=context)
        # Check output
        output_res = await self.check_output(answer, context=context, retrieved_chunks=retrieved_chunks)

        all_results = input_res.results + output_res.results
        action, blocked_reason, max_sev = self.policy.evaluate_results(all_results)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return GuardrailPipelineResult(
            passed=(action != GuardrailAction.BLOCK),
            action=action,
            blocked_reason=blocked_reason,
            max_severity=max_sev,
            results=all_results,
            latency_ms=elapsed_ms,
            target=GuardrailTarget.BOTH,
        )


def create_default_pipeline(
    policy: Optional[GuardrailPolicy] = None,
    grounding_threshold: float = 0.5,
    custom_pii_patterns: Optional[Dict[str, str]] = None,
) -> GuardrailPipeline:
    """Factory creating a standard production GuardrailPipeline."""
    guardrails: List[BaseGuardrail] = [
        PromptInjectionGuardrail(),
        PIIDetectionGuardrail(custom_patterns=custom_pii_patterns),
        PromptLeakageGuardrail(),
        GroundingGuardrail(grounding_threshold=grounding_threshold),
        SafetyGuardrail(),
    ]
    return GuardrailPipeline(guardrails=guardrails, policy=policy or GuardrailPolicy())
