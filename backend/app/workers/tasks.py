import asyncio
from typing import Optional
from uuid import UUID
from app.workers.celery_app import celery_app
from app.core.database import async_session_maker
from app.services.document_service import DocumentService

@celery_app.task(name="health_check_task")
def health_check_task():
    """Verify celery workers are operational."""
    return {"status": "success", "message": "Worker is healthy"}

@celery_app.task(name="process_document_task")
def process_document_task(
    document_id: str,
    file_bytes_base64: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 50
):
    """Celery worker task to process and index documents asynchronously."""
    import base64
    if file_bytes_base64 and not file_bytes:
        file_bytes = base64.b64decode(file_bytes_base64)

    async def _runner():
        async with async_session_maker() as session:
            await DocumentService.process_document_pipeline(
                document_id=UUID(document_id),
                file_bytes=file_bytes,
                db=session,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

    asyncio.run(_runner())
    return {"status": "success", "document_id": document_id}
