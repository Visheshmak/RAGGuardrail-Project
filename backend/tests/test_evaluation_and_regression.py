import pytest
import uuid
from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion, EvaluationCase
from app.models.evaluation import EvaluationRun, Baseline, RegressionResult, ProjectThresholdConfig
from app.core.security import create_access_token
from app.evaluation.metrics import (
    compute_accuracy,
    compute_retrieval_recall,
    compute_faithfulness,
    compute_answer_relevance,
)
from app.evaluation.regression import RegressionEngine, DEFAULT_THRESHOLDS
from app.services.evaluation_service import EvaluationService


# =====================================================================
# 1. EVALUATION METRICS TESTS
# =====================================================================

def test_compute_accuracy():
    # Exact match
    acc_exact = compute_accuracy("Employees get $750 stipend", "Employees get $750 stipend")
    assert acc_exact == 1.0

    # Partial match
    acc_partial = compute_accuracy("Employees receive $750 for office equipment", "Employees receive $750 stipend")
    assert 0.5 <= acc_partial < 1.0

    # Completely different
    acc_none = compute_accuracy("Apples and oranges are fruit", "Employees receive $750 stipend")
    assert acc_none == 0.0


def test_compute_retrieval_recall():
    golden_context = ["home office equipment stipend is $750", "20 days paid vacation"]
    
    # Full recall
    retrieved_full = [
        "Policy doc: home office equipment stipend is $750 for desks",
        "HR guide: employees get 20 days paid vacation annually"
    ]
    recall_full = compute_retrieval_recall(retrieved_full, golden_context)
    assert recall_full == 1.0

    # Partial recall (only 1 of 2 found)
    retrieved_half = ["Policy doc: home office equipment stipend is $750 for desks"]
    recall_half = compute_retrieval_recall(retrieved_half, golden_context)
    assert recall_half == 0.5

    # Zero recall
    retrieved_none = ["Company security handbook on passwords"]
    recall_none = compute_retrieval_recall(retrieved_none, golden_context)
    assert recall_none == 0.0


@pytest.mark.asyncio
async def test_compute_faithfulness():
    retrieved = ["Remote employees receive $750 for desk setup."]
    
    # Grounded answer
    faith_high = await compute_faithfulness("Employees receive $750 for desk setup.", retrieved)
    assert faith_high >= 0.8

    # Hallucinated answer
    faith_low = await compute_faithfulness("Employees receive $50,000 crypto bonus and free flights.", retrieved)
    assert faith_low <= 0.4


def test_compute_answer_relevance():
    q = "What is the equipment stipend amount?"
    a = "The equipment stipend amount is $750."
    rel = compute_answer_relevance(q, a)
    assert rel >= 0.7


# =====================================================================
# 2. REGRESSION ENGINE & REPRODUCIBLE DEMO TESTS
# =====================================================================

def test_reproducible_demo_scenario():
    """Reproducible demo test: Baseline 93%, Candidate 81% -> BLOCK."""
    baseline_metrics = {
        "accuracy": 0.93,
        "retrieval_recall": 0.93,
        "faithfulness": 0.95,
        "safety": 1.00,
    }
    candidate_metrics = {
        "accuracy": 0.81,
        "retrieval_recall": 0.81,
        "faithfulness": 0.88,
        "safety": 0.99,
    }
    thresholds = {
        "accuracy": {"minimum": 0.90, "max_regression": 0.05},
        "retrieval_recall": {"minimum": 0.85, "max_regression": 0.05},
        "faithfulness": {"minimum": 0.90, "max_regression": 0.03},
        "safety": {"minimum": 0.98, "max_regression": 0.01},
    }

    decision = RegressionEngine.compare(
        current_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        threshold_config=thresholds,
    )

    assert decision.decision == "BLOCK"
    assert decision.passed is False
    assert len(decision.reasons) >= 1
    # Check that accuracy or recall regression was caught
    flagged_metrics = [r["metric"] for r in decision.reasons]
    assert "accuracy" in flagged_metrics or "retrieval_recall" in flagged_metrics


def test_regression_engine_pass_scenario():
    baseline_metrics = {"accuracy": 0.92, "retrieval_recall": 0.90, "faithfulness": 0.92, "safety": 1.0}
    # Candidate is even better or very close
    candidate_metrics = {"accuracy": 0.94, "retrieval_recall": 0.91, "faithfulness": 0.93, "safety": 1.0}

    decision = RegressionEngine.compare(
        current_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )

    assert decision.decision == "PASS"
    assert decision.passed is True
    assert len(decision.reasons) == 0


def test_regression_engine_warning_scenario():
    baseline_metrics = {"accuracy": 0.95, "retrieval_recall": 0.90, "faithfulness": 0.95, "safety": 1.0}
    # Small dip within allowed regression limit but approaching limit (0.02 drop with 0.03 max)
    candidate_metrics = {"accuracy": 0.928, "retrieval_recall": 0.90, "faithfulness": 0.95, "safety": 1.0}

    decision = RegressionEngine.compare(
        current_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
    )

    assert decision.decision in ("WARNING", "PASS")
    assert decision.passed is True


def test_regression_engine_guardrail_blocking():
    baseline_metrics = {"accuracy": 0.95, "retrieval_recall": 0.90, "faithfulness": 0.95, "safety": 1.0}
    candidate_metrics = {"accuracy": 0.95, "retrieval_recall": 0.90, "faithfulness": 0.95, "safety": 1.0}

    # Critical guardrail violation occurred
    decision = RegressionEngine.compare(
        current_metrics=candidate_metrics,
        baseline_metrics=baseline_metrics,
        guardrail_summary={"critical_violations": 1, "total_violations": 1},
        block_on_critical_guardrail=True
    )

    assert decision.decision == "BLOCK"
    assert decision.passed is False
    assert any(r.get("metric") == "guardrails" for r in decision.reasons)


# =====================================================================
# 3. BASELINE LIFECYCLE & DATABASE SERVICE TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_baseline_promotion_single_active(db_session, test_user):
    project = Project(name="Baseline Lifecycle Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 1. Create run 1
    run1 = EvaluationRun(
        project_id=project.id,
        name="Run v1",
        status="COMPLETED",
        metrics={"accuracy": 0.91, "faithfulness": 0.92},
        guardrail_summary={},
        configuration_snapshot={"model": "gpt-4"}
    )
    db_session.add(run1)
    await db_session.commit()
    await db_session.refresh(run1)

    # 2. Promote run 1 to baseline
    base1 = await EvaluationService.set_active_baseline(
        project_id=project.id,
        evaluation_run_id=run1.id,
        notes="First golden baseline",
        db=db_session
    )
    assert base1.version == 1
    assert base1.is_active is True

    # 3. Create run 2 and promote to baseline
    run2 = EvaluationRun(
        project_id=project.id,
        name="Run v2",
        status="COMPLETED",
        metrics={"accuracy": 0.95, "faithfulness": 0.96},
        guardrail_summary={},
        configuration_snapshot={"model": "gpt-4"}
    )
    db_session.add(run2)
    await db_session.commit()
    await db_session.refresh(run2)

    base2 = await EvaluationService.set_active_baseline(
        project_id=project.id,
        evaluation_run_id=run2.id,
        notes="Second improved baseline",
        db=db_session
    )
    assert base2.version == 2
    assert base2.is_active is True

    # 4. Verify base1 is now inactive
    await db_session.refresh(base1)
    assert base1.is_active is False

    # 5. Verify get_active_baseline returns base2
    active = await EvaluationService.get_active_baseline(project.id, db_session)
    assert active.id == base2.id


# =====================================================================
# 4. API INTEGRATION & RELEASE DECISION ENDPOINTS TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_evaluation_and_regression_api_flow(client, test_user, db_session):
    project = Project(name="API Regression Flow Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create baseline and candidate records from completed test data.
    run1 = EvaluationRun(
        project_id=project.id,
        name="Production Golden Run v1",
        status="COMPLETED",
        metrics={"accuracy": 0.93, "retrieval_recall": 0.93, "faithfulness": 0.94, "safety": 1.0},
        guardrail_summary={"critical_violations": 0},
        configuration_snapshot={"model": "test"}
    )
    db_session.add(run1)
    await db_session.commit()
    await db_session.refresh(run1)
    run1_id = str(run1.id)

    # 2. Promote Run 1 to Baseline
    base_payload = {"evaluation_run_id": run1_id, "notes": "Production baseline"}
    base_resp = await client.post(
        f"/api/v1/projects/{project.id}/baselines",
        json=base_payload,
        headers=headers
    )
    assert base_resp.status_code == 201
    assert base_resp.json()["is_active"] is True
    assert base_resp.json()["version"] == 1

    # 3. Persist a candidate run with a genuine regression for comparison.
    run2 = EvaluationRun(
        project_id=project.id,
        name="Experimental Candidate v2",
        status="COMPLETED",
        metrics={"accuracy": 0.81, "retrieval_recall": 0.81, "faithfulness": 0.88, "safety": 0.99},
        guardrail_summary={"critical_violations": 0},
        configuration_snapshot={"model": "test"}
    )
    db_session.add(run2)
    await db_session.commit()
    await db_session.refresh(run2)
    run2_id = str(run2.id)

    # 4. Compare Candidate against Baseline
    compare_resp = await client.post(
        f"/api/v1/projects/{project.id}/evaluations/{run2_id}/compare",
        headers=headers
    )
    assert compare_resp.status_code == 200
    compare_data = compare_resp.json()
    assert compare_data["decision"] == "BLOCK"
    assert compare_data["passed"] is False
    assert len(compare_data["reasons"]) >= 1

    # 5. Fetch Release Decision
    decision_resp = await client.get(
        f"/api/v1/projects/{project.id}/evaluations/{run2_id}/release-decision",
        headers=headers
    )
    assert decision_resp.status_code == 200
    decision_data = decision_resp.json()
    assert decision_data["decision"] == "BLOCK"
    assert decision_data["passed"] is False

    # 6. Check Project Thresholds update
    thresh_resp = await client.get(f"/api/v1/projects/{project.id}/thresholds", headers=headers)
    assert thresh_resp.status_code == 200
    assert "accuracy" in thresh_resp.json()["thresholds"]
