from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import os

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.document import Document, DocumentStatus
from app.models.chunk import DocumentChunk
from app.schemas.document import DocumentResponse, DocumentChunkResponse
from app.api.deps import get_current_user
from app.services.document_service import DocumentService
from app.rag.vector_store import vector_store

router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".markdown"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

async def _verify_project_access(project_id: UUID, current_user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")
    return project

@router.post("/{project_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)

    # Validate filename and extension
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")
    
    _, ext = os.path.splitext(file.filename)
    clean_ext = ext.lower()
    if clean_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported formats: PDF, DOCX, TXT, MD"
        )

    # Read and validate size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 25MB limit.")

    # Create document entry in QUEUED state
    doc = Document(
        project_id=project_id,
        filename=file.filename,
        file_type=clean_ext.strip("."),
        file_size=file_size,
        status=DocumentStatus.QUEUED,
        chunking_config={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap}
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Execute ingestion via background task
    async def _process_task():
        from app.core.database import async_session_maker
        async with async_session_maker() as session:
            await DocumentService.process_document_pipeline(
                document_id=doc.id,
                file_bytes=file_bytes,
                db=session,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

    background_tasks.add_task(_process_task)

    return doc

@router.get("/{project_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{project_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    project_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc

@router.get("/{project_id}/documents/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def list_document_chunks(
    project_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.project_id == project_id
        ).order_by(DocumentChunk.chunk_index.asc())
    )
    return result.scalars().all()

@router.delete("/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    await _verify_project_access(project_id, current_user, db)
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete vectors from Qdrant
    await vector_store.delete_by_document(document_id)

    # Delete from DB
    await db.delete(doc)
    await db.commit()
    return None
