from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.guardrail import ProjectGuardrailConfig, GuardrailExecutionLog
from app.schemas.guardrail import (
    GuardrailCheckRequest,
    GuardrailCheckResponse,
    ProjectGuardrailConfigCreate,
    ProjectGuardrailConfigUpdate,
    ProjectGuardrailConfigResponse,
    GuardrailExecutionLogResponse,
)
from app.api.deps import get_current_user
from app.services.guardrail_service import GuardrailService
from app.guardrails.base import GuardrailTarget

router = APIRouter()


async def _verify_project_access(project_id: UUID, current_user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")
    return project


@router.get("/{project_id}/guardrails", response_model=List[ProjectGuardrailConfigResponse])
async def list_guardrails(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(ProjectGuardrailConfig)
        .where(ProjectGuardrailConfig.project_id == project_id)
        .order_by(ProjectGuardrailConfig.created_at.asc())
    )
    configs = result.scalars().all()

    # Seed defaults if empty
    if not configs:
        configs = await GuardrailService.seed_default_configs(project_id, db)

    return configs


@router.post("/{project_id}/guardrails", response_model=ProjectGuardrailConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_guardrail(
    project_id: UUID,
    config_in: ProjectGuardrailConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    cfg = ProjectGuardrailConfig(
        project_id=project_id,
        guardrail_type=config_in.guardrail_type,
        name=config_in.name,
        description=config_in.description,
        target=config_in.target,
        is_enabled=config_in.is_enabled,
        severity_override=config_in.severity_override,
        action_override=config_in.action_override,
        parameters=config_in.parameters
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.put("/{project_id}/guardrails/{guardrail_id}", response_model=ProjectGuardrailConfigResponse)
async def update_guardrail(
    project_id: UUID,
    guardrail_id: UUID,
    config_in: ProjectGuardrailConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(ProjectGuardrailConfig).where(
            ProjectGuardrailConfig.id == guardrail_id,
            ProjectGuardrailConfig.project_id == project_id
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail configuration not found")

    update_data = config_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(cfg, field, val)

    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.delete("/{project_id}/guardrails/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(
    project_id: UUID,
    guardrail_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(ProjectGuardrailConfig).where(
            ProjectGuardrailConfig.id == guardrail_id,
            ProjectGuardrailConfig.project_id == project_id
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardrail configuration not found")

    await db.delete(cfg)
    await db.commit()
    return None


@router.post("/{project_id}/guardrails/test", response_model=GuardrailCheckResponse)
async def test_guardrails(
    project_id: UUID,
    payload: GuardrailCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test guardrail pipeline on arbitrary input/output text and optionally log execution."""
    await _verify_project_access(project_id, current_user, db)

    pipeline = await GuardrailService.get_pipeline_for_project(project_id, db)
    context = {
        "retrieved_chunks": payload.retrieved_chunks,
        "system_prompt": payload.system_prompt,
        **(payload.custom_parameters or {})
    }

    if payload.target == GuardrailTarget.INPUT:
        res = await pipeline.check_input(payload.text, context=context)
    elif payload.target == GuardrailTarget.OUTPUT:
        res = await pipeline.check_output(payload.text, context=context, retrieved_chunks=payload.retrieved_chunks)
    else:
        # Check both using input logic for the single test text
        res = await pipeline.check_input(payload.text, context=context)

    # Record execution log
    await GuardrailService.log_execution_results(
        project_id=project_id,
        results=res.results,
        target=payload.target.value,
        policy=pipeline.policy,
        latency_ms=res.latency_ms,
        db=db
    )

    return GuardrailCheckResponse(
        passed=res.passed,
        action=res.action,
        blocked_reason=res.blocked_reason,
        max_severity=res.max_severity,
        results=res.results,
        latency_ms=res.latency_ms,
        target=payload.target
    )


@router.get("/{project_id}/guardrails/logs", response_model=List[GuardrailExecutionLogResponse])
async def list_guardrail_logs(
    project_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    passed_only: Optional[bool] = None,
    guardrail_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    query = select(GuardrailExecutionLog).where(
        GuardrailExecutionLog.project_id == project_id
    )
    if passed_only is not None:
        query = query.where(GuardrailExecutionLog.passed == passed_only)
    if guardrail_name:
        query = query.where(GuardrailExecutionLog.guardrail_name == guardrail_name)

    query = query.order_by(GuardrailExecutionLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
