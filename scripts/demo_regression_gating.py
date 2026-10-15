"""Reproducible Demo for RAGGuard Part 7: Regression Engine & Release Gating.

Scenario:
- Baseline Evaluation: 93% accuracy / retrieval recall
- Candidate Evaluation: 81% accuracy / retrieval recall
- Max Allowed Regression: 5% (0.05)
- Actual Regression: 12% (0.12)
- Expected Release Decision: BLOCK
"""

import os
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set default env vars if not present
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("JWT_SECRET", "demo-secret-key-12345")
os.environ.setdefault("OPENAI_API_KEY", "mock-openai-key")

from app.evaluation.regression import RegressionEngine, DEFAULT_THRESHOLDS


def run_demo():
    print("=" * 65)
    print("   RAGGuard — Regression Engine & Release Gating Demo")
    print("=" * 65)

    # 1. Baseline Run Metrics (93%)
    baseline_metrics = {
        "accuracy": 0.93,
        "retrieval_recall": 0.93,
        "faithfulness": 0.95,
        "safety": 1.00,
    }

    # 2. Candidate Run Metrics (81% - Regressed by 12%)
    candidate_metrics = {
        "accuracy": 0.81,
        "retrieval_recall": 0.81,
        "faithfulness": 0.88,
        "safety": 0.99,
    }

    # 3. Per-project threshold configuration
    threshold_config = {
        "accuracy": {"minimum": 0.90, "max_regression": 0.05},
        "retrieval_recall": {"minimum": 0.85, "max_regression": 0.05},
        "faithfulness": {"minimum": 0.90, "max_regression": 0.03},
        "safety": {"minimum": 0.98, "max_regression": 0.01},
    }

    print("\n[1] Active Baseline Metrics:")
    for k, v in baseline_metrics.items():
        print(f"    - {k:18}: {v * 100:.1f}%")

    print("\n[2] Candidate Evaluation Metrics:")
    for k, v in candidate_metrics.items():
        print(f"    - {k:18}: {v * 100:.1f}%")

    print("\n[3] Evaluating Regression & Release Gate Decision...")
    decision = RegressionEngine.compare(
        current_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        threshold_config=threshold_config,
        guardrail_summary={"critical_violations": 0}
    )

    print("\n" + "=" * 65)
    print(f"   RELEASE DECISION: {decision.decision}")
    print(f"   GATE PASSED:      {decision.passed}")
    print("=" * 65)

    print("\n[4] Structured Gating Reasons:")
    print(json.dumps(decision.reasons, indent=2))

    print("\n[5] Per-Metric Comparison Table:")
    for m in decision.metrics_comparison:
        print(f"    - {m.metric:18} | Base: {m.baseline:.2f} | Current: {m.current:.2f} | Reg: {m.actual_regression:.2f} (Allowed: {m.allowed_regression:.2f}) | Status: {m.status}")

    # Validation assertion
    assert decision.decision == "BLOCK", f"Expected BLOCK but got {decision.decision}"
    assert decision.passed is False
    print("\n>>> DEMO SUCCEEDED: System successfully detected 12% regression and BLOCKED release! <<<\n")


if __name__ == "__main__":
    run_demo()
