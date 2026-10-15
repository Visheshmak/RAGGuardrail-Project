from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=current_user.id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        result = await db.execute(select(Project))
    else:
        result = await db.execute(select(Project).where(Project.owner_id == current_user.id))
    return result.scalars().all()

@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Project).where(Project.id == id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")
        
    return project

@router.put("/{id}", response_model=ProjectResponse)
async def update_project(
    id: UUID,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Project).where(Project.id == id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")
        
    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
        
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Project).where(Project.id == id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")
        
    await db.delete(project)
    await db.commit()
    return None
