from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.evaluation import EvaluationRun, Baseline, RegressionResult, ProjectThresholdConfig
from app.schemas.evaluation import (
    EvaluationRunCreate,
    EvaluationRunResponse,
    BaselineCreate,
    BaselineResponse,
    RegressionResultResponse,
    ReleaseDecisionResponse,
    ProjectThresholdConfigUpdate,
    ProjectThresholdConfigResponse,
)
from app.api.deps import get_current_user
from app.services.evaluation_service import EvaluationService
from app.evaluation.engine import EvaluationEngine

router = APIRouter()


async def _verify_project_access(project_id: UUID, current_user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")
    return project


# ==========================================
# EVALUATION RUNS ENDPOINTS
# ==========================================

@router.post("/projects/{project_id}/evaluations", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation_run(
    project_id: UUID,
    payload: EvaluationRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute an evaluation run against a persisted dataset version."""
    await _verify_project_access(project_id, current_user, db)

    if payload.dataset_version_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset_version_id is required to execute an evaluation"
        )

    # Run execution engine over dataset version cases
    eval_run = await EvaluationEngine.run_evaluation(
        project_id=project_id,
        dataset_version_id=payload.dataset_version_id,
        run_name=payload.name,
        db=db,
        configuration_snapshot=payload.configuration_snapshot
    )
    return eval_run


@router.get("/projects/{project_id}/evaluations", response_model=List[EvaluationRunResponse])
async def list_evaluation_runs(
    project_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(EvaluationRun)
        .where(EvaluationRun.project_id == project_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/projects/{project_id}/evaluations/{evaluation_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    project_id: UUID,
    evaluation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(EvaluationRun).where(
            EvaluationRun.id == evaluation_id,
            EvaluationRun.project_id == project_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")
    return run


# ==========================================
# BASELINES ENDPOINTS
# ==========================================

@router.post("/projects/{project_id}/baselines", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED)
async def create_baseline_for_project(
    project_id: UUID,
    payload: BaselineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Promote an evaluation run to be the project's active baseline."""
    await _verify_project_access(project_id, current_user, db)
    try:
        baseline = await EvaluationService.set_active_baseline(
            project_id=project_id,
            evaluation_run_id=payload.evaluation_run_id,
            notes=payload.notes,
            db=db
        )
        return baseline
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/projects/{project_id}/baselines", response_model=List[BaselineResponse])
async def list_baselines_for_project(
    project_id: UUID,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List baseline history or active baseline for a project."""
    await _verify_project_access(project_id, current_user, db)
    query = select(Baseline).where(Baseline.project_id == project_id)
    if active_only:
        query = query.where(Baseline.is_active == True)
    query = query.order_by(Baseline.version.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Root-level /baselines route helper
@router.post("/baselines", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED)
async def create_baseline_global(
    payload: BaselineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Global baseline promotion endpoint finding project automatically from evaluation run."""
    run_res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == payload.evaluation_run_id))
    eval_run = run_res.scalar_one_or_none()
    if not eval_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")

    await _verify_project_access(eval_run.project_id, current_user, db)
    baseline = await EvaluationService.set_active_baseline(
        project_id=eval_run.project_id,
        evaluation_run_id=payload.evaluation_run_id,
        notes=payload.notes,
        db=db
    )
    return baseline


@router.get("/baselines", response_model=List[BaselineResponse])
async def list_baselines_global(
    project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Global baselines listing endpoint."""
    if project_id:
        await _verify_project_access(project_id, current_user, db)
        query = select(Baseline).where(Baseline.project_id == project_id).order_by(Baseline.version.desc())
    else:
        query = select(Baseline).order_by(Baseline.created_at.desc()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


# ==========================================
# REGRESSION COMPARISON & RELEASE DECISION
# ==========================================

@router.post("/evaluations/{evaluation_id}/compare", response_model=ReleaseDecisionResponse)
@router.post("/projects/{project_id}/evaluations/{evaluation_id}/compare", response_model=ReleaseDecisionResponse)
async def compare_evaluation_run(
    evaluation_id: UUID,
    project_id: Optional[UUID] = None,
    baseline_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare candidate evaluation against active baseline and store regression results."""
    run_res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == evaluation_id))
    eval_run = run_res.scalar_one_or_none()
    if not eval_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")

    p_id = project_id or eval_run.project_id
    await _verify_project_access(p_id, current_user, db)

    try:
        decision, _ = await EvaluationService.compare_run_against_baseline(
            project_id=p_id,
            evaluation_run_id=evaluation_id,
            baseline_id=baseline_id,
            db=db
        )
        return ReleaseDecisionResponse(
            decision=decision.decision,
            passed=decision.passed,
            reasons=decision.reasons,
            metrics_comparison=[m.model_dump() for m in decision.metrics_comparison],
            baseline_version=decision.baseline_version,
            evaluation_run_id=eval_run.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/evaluations/{evaluation_id}/release-decision", response_model=ReleaseDecisionResponse)
@router.get("/projects/{project_id}/evaluations/{evaluation_id}/release-decision", response_model=ReleaseDecisionResponse)
async def get_release_decision(
    evaluation_id: UUID,
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch the release gating decision for an evaluation run against the active baseline."""
    run_res = await db.execute(select(EvaluationRun).where(EvaluationRun.id == evaluation_id))
    eval_run = run_res.scalar_one_or_none()
    if not eval_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found")

    p_id = project_id or eval_run.project_id
    await _verify_project_access(p_id, current_user, db)

    try:
        decision, _ = await EvaluationService.compare_run_against_baseline(
            project_id=p_id,
            evaluation_run_id=evaluation_id,
            baseline_id=None,
            db=db
        )
        return ReleaseDecisionResponse(
            decision=decision.decision,
            passed=decision.passed,
            reasons=decision.reasons,
            metrics_comparison=[m.model_dump() for m in decision.metrics_comparison],
            baseline_version=decision.baseline_version,
            evaluation_run_id=eval_run.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# THRESHOLDS CONFIGURATION ENDPOINTS
# ==========================================

@router.get("/projects/{project_id}/thresholds", response_model=ProjectThresholdConfigResponse)
async def get_project_thresholds(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    cfg = await EvaluationService.get_or_create_threshold_config(project_id, db)
    return cfg


@router.put("/projects/{project_id}/thresholds", response_model=ProjectThresholdConfigResponse)
async def update_project_thresholds(
    project_id: UUID,
    payload: ProjectThresholdConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    cfg = await EvaluationService.get_or_create_threshold_config(project_id, db)

    if payload.thresholds is not None:
        # Merge updated thresholds with existing
        merged = {**cfg.thresholds, **payload.thresholds}
        cfg.thresholds = merged
    if payload.block_on_critical_guardrail is not None:
        cfg.block_on_critical_guardrail = payload.block_on_critical_guardrail
    if payload.settings is not None:
        cfg.settings = {**(cfg.settings or {}), **payload.settings}

    await db.commit()
    await db.refresh(cfg)
    return cfg
