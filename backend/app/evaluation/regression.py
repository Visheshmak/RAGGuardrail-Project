from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


DEFAULT_THRESHOLDS = {
    "accuracy": {"minimum": 0.90, "max_regression": 0.03},
    "faithfulness": {"minimum": 0.90, "max_regression": 0.03},
    "retrieval_recall": {"minimum": 0.85, "max_regression": 0.05},
    "safety": {"minimum": 0.98, "max_regression": 0.01},
}


class MetricRegressionDetail(BaseModel):
    metric: str
    baseline: float
    current: float
    allowed_regression: float
    actual_regression: float
    status: str  # PASS, WARNING, FAIL
    reason: Optional[str] = None


class ReleaseDecision(BaseModel):
    decision: str = Field(..., description="Release decision: PASS, WARNING, BLOCK")
    passed: bool = Field(..., description="True if not BLOCK")
    reasons: List[Dict[str, Any]] = Field(default_factory=list, description="Structured blocking or warning reasons")
    metrics_comparison: List[MetricRegressionDetail] = Field(default_factory=list, description="Per-metric detailed comparison")
    baseline_version: Optional[int] = None
    evaluation_run_id: Optional[str] = None


class RegressionEngine:
    """Core engine to evaluate candidate evaluations against baseline snapshots and gating policies."""

    @staticmethod
    def compare(
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
        threshold_config: Optional[Dict[str, Dict[str, float]]] = None,
        guardrail_summary: Optional[Dict[str, Any]] = None,
        block_on_critical_guardrail: bool = True
    ) -> ReleaseDecision:
        """Compare current metrics against baseline metrics and produce a ReleaseDecision."""
        thresholds = {**DEFAULT_THRESHOLDS, **(threshold_config or {})}
        guardrail_summary = guardrail_summary or {}

        comparison_details: List[MetricRegressionDetail] = []
        blocking_reasons: List[Dict[str, Any]] = []
        warning_reasons: List[Dict[str, Any]] = []

        # 1. Check critical guardrail violations
        critical_violations = guardrail_summary.get("critical_violations", 0)
        if block_on_critical_guardrail and critical_violations > 0:
            blocking_reasons.append({
                "metric": "guardrails",
                "reason": f"Detected {critical_violations} critical guardrail violation(s)",
                "critical_violations": critical_violations
            })

        # 2. Evaluate each metric
        all_metric_keys = set(baseline_metrics.keys()).union(set(current_metrics.keys()))

        for metric in all_metric_keys:
            baseline_val = float(baseline_metrics.get(metric, 1.0))
            current_val = float(current_metrics.get(metric, 0.0))

            metric_cfg = thresholds.get(metric, {"minimum": 0.0, "max_regression": 0.05})
            minimum = float(metric_cfg.get("minimum", 0.0))
            max_reg = float(metric_cfg.get("max_regression", 0.05))

            # Actual regression is drop from baseline: baseline - current
            actual_drop = round(baseline_val - current_val, 4)
            abs_diff = round(current_val - baseline_val, 4)

            # Determine status
            if current_val < minimum:
                status = "FAIL"
                reason_msg = f"{metric} ({round(current_val, 4)}) is below minimum threshold ({minimum})"
                blocking_reasons.append({
                    "metric": metric,
                    "baseline": round(baseline_val, 4),
                    "current": round(current_val, 4),
                    "minimum_required": minimum,
                    "reason": reason_msg
                })
            elif actual_drop > max_reg:
                status = "FAIL"
                reason_msg = f"{metric} regressed by {actual_drop} (exceeds allowed {max_reg})"
                blocking_reasons.append({
                    "metric": metric,
                    "baseline": round(baseline_val, 4),
                    "current": round(current_val, 4),
                    "allowed_regression": max_reg,
                    "actual_regression": actual_drop,
                    "reason": reason_msg
                })
            elif actual_drop > (max_reg * 0.7) and actual_drop > 0:
                status = "WARNING"
                reason_msg = f"{metric} warning: regression {actual_drop} approaching limit {max_reg}"
                warning_reasons.append({
                    "metric": metric,
                    "baseline": round(baseline_val, 4),
                    "current": round(current_val, 4),
                    "allowed_regression": max_reg,
                    "actual_regression": actual_drop,
                    "reason": reason_msg
                })
            else:
                status = "PASS"
                reason_msg = None

            comparison_details.append(
                MetricRegressionDetail(
                    metric=metric,
                    baseline=round(baseline_val, 4),
                    current=round(current_val, 4),
                    allowed_regression=max_reg,
                    actual_regression=max(actual_drop, 0.0),
                    status=status,
                    reason=reason_msg
                )
            )

        # 3. Determine Overall Decision
        if blocking_reasons:
            decision = "BLOCK"
            passed = False
            reasons_output = blocking_reasons
        elif warning_reasons:
            decision = "WARNING"
            passed = True
            reasons_output = warning_reasons
        else:
            decision = "PASS"
            passed = True
            reasons_output = []

        return ReleaseDecision(
            decision=decision,
            passed=passed,
            reasons=reasons_output,
            metrics_comparison=comparison_details
        )
