import os
import uuid
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document, DocumentStatus
from app.models.chunk import DocumentChunk
from app.rag.extractors import DocumentExtractor
from app.rag.chunker import RecursiveTextChunker
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import vector_store, VectorPoint

class DocumentService:
    @staticmethod
    async def process_document_pipeline(
        document_id: UUID,
        file_bytes: bytes,
        db: AsyncSession,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> Document:
        """Complete ingestion pipeline: extraction -> cleaning -> chunking -> embedding -> DB & Qdrant."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        try:
            # 1. Update status to PROCESSING
            document.status = DocumentStatus.PROCESSING
            document.error_message = None
            document.chunking_config = {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            }
            await db.commit()
            await db.refresh(document)

            # 2. Extract text with cleaning
            pages = DocumentExtractor.extract(file_bytes, document.file_type)
            if not pages:
                raise ValueError(f"No extractable text found in file '{document.filename}'")

            # 3. Chunk text
            chunker = RecursiveTextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            raw_chunks = chunker.chunk_extracted_pages(pages)
            if not raw_chunks:
                raise ValueError("Text chunking produced zero chunks.")

            # 4. Generate embeddings
            embedding_provider = get_embedding_provider()
            chunk_texts = [c.text for c in raw_chunks]
            embeddings = await embedding_provider.embed_documents(chunk_texts)

            # 5. Save chunks to database & prepare vector points
            vector_points: List[VectorPoint] = []
            db_chunks: List[DocumentChunk] = []

            for raw_chunk, embedding in zip(raw_chunks, embeddings):
                chunk_id = uuid.uuid4()
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    project_id=document.project_id,
                    text=raw_chunk.text,
                    chunk_index=raw_chunk.chunk_index,
                    page_number=raw_chunk.page_number,
                    chunk_metadata=raw_chunk.metadata,
                )
                db_chunks.append(db_chunk)

                vector_points.append(
                    VectorPoint(
                        id=str(chunk_id),
                        vector=embedding,
                        payload={
                            "document_id": str(document.id),
                            "project_id": str(document.project_id),
                            "filename": document.filename,
                            "page_number": raw_chunk.page_number,
                            "chunk_index": raw_chunk.chunk_index,
                            "text": raw_chunk.text,
                            "metadata": raw_chunk.metadata,
                        }
                    )
                )

            # 6. Store in Qdrant
            await vector_store.upsert_points(
                points=vector_points,
                vector_size=embedding_provider.dimension
            )

            # 7. Commit DB chunks and mark COMPLETED
            db.add_all(db_chunks)
            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(db_chunks)
            await db.commit()
            await db.refresh(document)
            return document

        except Exception as e:
            await db.rollback()
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await db.commit()
            await db.refresh(document)
            raise e
