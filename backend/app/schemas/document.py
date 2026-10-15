from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.document import DocumentStatus

class ChunkingConfigSchema(BaseModel):
    chunk_size: int = Field(500, ge=50, le=4000)
    chunk_overlap: int = Field(50, ge=0, le=1000)

class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: int = 0
    chunking_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    project_id: UUID
    text: str
    chunk_index: int
    page_number: Optional[int] = None
    chunk_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
