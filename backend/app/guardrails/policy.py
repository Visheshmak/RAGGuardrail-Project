from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.guardrails.base import (
    GuardrailAction,
    GuardrailResult,
    GuardrailSeverity,
)


class GuardrailPolicy(BaseModel):
    """Configurable severity-to-action policy engine."""

    severity_actions: Dict[GuardrailSeverity, GuardrailAction] = Field(
        default_factory=lambda: {
            GuardrailSeverity.CRITICAL: GuardrailAction.BLOCK,
            GuardrailSeverity.HIGH: GuardrailAction.BLOCK,
            GuardrailSeverity.MEDIUM: GuardrailAction.WARNING,
            GuardrailSeverity.LOW: GuardrailAction.LOG,
        }
    )
    block_on_warning: bool = False

    def get_action_for_severity(self, severity: GuardrailSeverity) -> GuardrailAction:
        action = self.severity_actions.get(severity, GuardrailAction.LOG)
        if action == GuardrailAction.WARNING and self.block_on_warning:
            return GuardrailAction.BLOCK
        return action

    def evaluate_results(
        self, results: List[GuardrailResult]
    ) -> Tuple[GuardrailAction, Optional[str], Optional[GuardrailSeverity]]:
        """Evaluate aggregated results against policy and determine overall system action.
        
        Returns:
            (overall_action, blocked_reason, max_severity)
        """
        if not results:
            return GuardrailAction.ALLOW, None, None

        failed_results = [r for r in results if not r.passed]
        if not failed_results:
            return GuardrailAction.ALLOW, None, None

        # Determine highest severity among failures
        severity_order = [
            GuardrailSeverity.CRITICAL,
            GuardrailSeverity.HIGH,
            GuardrailSeverity.MEDIUM,
            GuardrailSeverity.LOW,
        ]

        max_severity = None
        for sev in severity_order:
            if any(r.severity == sev for r in failed_results):
                max_severity = sev
                break

        if max_severity is None:
            max_severity = GuardrailSeverity.LOW

        # Find corresponding action
        overall_action = self.get_action_for_severity(max_severity)

        # Construct primary reason
        critical_or_high_failures = [
            r for r in failed_results if r.severity in (GuardrailSeverity.CRITICAL, GuardrailSeverity.HIGH)
        ]
        if critical_or_high_failures:
            reasons = [f"[{r.guardrail}] {r.reason}" for r in critical_or_high_failures]
            blocked_reason = "; ".join(reasons)
        else:
            reasons = [f"[{r.guardrail}] {r.reason}" for r in failed_results]
            blocked_reason = "; ".join(reasons)

        return overall_action, blocked_reason, max_severity
