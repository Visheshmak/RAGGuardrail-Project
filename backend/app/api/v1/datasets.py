import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion, EvaluationCase
from app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetVersionResponse,
    EvaluationCaseResponse,
    CreateVersionRequest,
    DatasetStatistics,
    DatasetUploadSummary
)
from app.api.deps import get_current_user
from app.services.dataset_service import DatasetService, DatasetParser, DatasetValidationError

router = APIRouter()

async def _verify_dataset_access(dataset_id: UUID, current_user: User, db: AsyncSession) -> Dataset:
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.versions))
        .where(Dataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    # Verify project ownership
    res_proj = await db.execute(select(Project).where(Project.id == dataset.project_id))
    project = res_proj.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent project not found")

    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this dataset")

    return dataset

@router.post("/projects/{project_id}/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    project_id: UUID,
    dataset_in: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project access
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this project")

    dataset = await DatasetService.create_dataset_with_version(
        project_id=project_id,
        name=dataset_in.name,
        description=dataset_in.description,
        cases=dataset_in.initial_cases,
        db=db
    )
    
    # Reload with versions
    reloaded = await db.execute(
        select(Dataset).options(selectinload(Dataset.versions)).where(Dataset.id == dataset.id)
    )
    return reloaded.scalar_one()

@router.get("/projects/{project_id}/datasets", response_model=List[DatasetResponse])
async def list_project_datasets(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this project")

    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.versions))
        .where(Dataset.project_id == project_id)
        .order_by(Dataset.created_at.desc())
    )
    datasets = result.scalars().all()
    
    # Calculate computed summary fields
    for d in datasets:
        if d.versions:
            d.latest_version = d.versions[0].version
            d.total_cases = d.versions[0].case_count
        else:
            d.latest_version = 0
            d.total_cases = 0
            
    return datasets

@router.get("/datasets/{id}", response_model=DatasetResponse)
async def get_dataset(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = await _verify_dataset_access(id, current_user, db)
    if dataset.versions:
        dataset.latest_version = dataset.versions[0].version
        dataset.total_cases = dataset.versions[0].case_count
    else:
        dataset.latest_version = 0
        dataset.total_cases = 0
    return dataset

@router.get("/datasets/{id}/versions", response_model=List[DatasetVersionResponse])
async def list_dataset_versions(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = await _verify_dataset_access(id, current_user, db)
    return dataset.versions

@router.post("/datasets/{id}/versions", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset_version(
    id: UUID,
    version_in: CreateVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_dataset_access(id, current_user, db)
    version = await DatasetService.add_dataset_version(
        dataset_id=id,
        cases=version_in.cases,
        description=version_in.description,
        db=db
    )
    return version

@router.post("/datasets/{id}/upload", response_model=DatasetUploadSummary, status_code=status.HTTP_201_CREATED)
async def upload_dataset_file(
    id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_dataset_access(id, current_user, db)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".csv", ".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported dataset format '{ext}'. Must be CSV or JSON."
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        if ext == ".json":
            cases, summary = DatasetParser.parse_json(content)
        else:
            cases, summary = DatasetParser.parse_csv(content)
    except DatasetValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(ve), "errors": ve.errors}
        )

    # Add version to database
    desc = description or f"Imported from {file.filename}"
    version = await DatasetService.add_dataset_version(
        dataset_id=id,
        cases=cases,
        description=desc,
        db=db
    )

    summary.dataset_id = id
    summary.version_id = version.id
    summary.version = version.version
    return summary

@router.get("/datasets/{id}/versions/{version_id}/cases", response_model=List[EvaluationCaseResponse])
async def list_version_cases(
    id: UUID,
    version_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_dataset_access(id, current_user, db)

    stmt = select(EvaluationCase).where(EvaluationCase.dataset_version_id == version_id)
    if category:
        stmt = stmt.where(EvaluationCase.category == category)
    if difficulty:
        stmt = stmt.where(EvaluationCase.difficulty == difficulty)

    stmt = stmt.order_by(EvaluationCase.created_at.asc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/datasets/{id}/versions/{version_id}/stats", response_model=DatasetStatistics)
async def get_version_statistics(
    id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_dataset_access(id, current_user, db)
    stats = await DatasetService.get_version_statistics(version_id, db)
    return stats

@router.delete("/datasets/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dataset = await _verify_dataset_access(id, current_user, db)
    await db.delete(dataset)
    await db.commit()
    return None
