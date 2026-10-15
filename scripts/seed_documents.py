import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.document import Document, DocumentStatus
from app.core.security import get_password_hash
from app.services.document_service import DocumentService
from app.rag.rag_service import get_rag_service

DOCUMENTS_DIR = Path(__file__).parent.parent / "data" / "documents"

async def seed():
    print("=" * 60)
    print(" RAGGuard — Seed Demo Documents & Pipeline Setup")
    print("=" * 60)

    async with async_session_maker() as session:
        # 1. Create or fetch Demo User
        user_email = "demo@ragguard.io"
        res = await session.execute(select(User).where(User.email == user_email))
        user = res.scalar_one_or_none()
        if not user:
            print(f"[+] Creating demo user: {user_email}")
            user = User(
                email=user_email,
                name="Demo Engineer",
                password_hash=get_password_hash("password123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            print(f"[*] Demo user already exists: {user_email}")

        # 2. Create or fetch Demo Project
        project_name = "Enterprise HR & Compliance Knowledge Base"
        res = await session.execute(select(Project).where(Project.name == project_name, Project.owner_id == user.id))
        project = res.scalar_one_or_none()
        if not project:
            print(f"[+] Creating demo project: '{project_name}'")
            project = Project(
                name=project_name,
                description="Demo knowledge base containing remote work, benefits, and security guidelines.",
                owner_id=user.id
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
        else:
            print(f"[*] Demo project already exists: '{project_name}' (ID: {project.id})")

        # 3. Read and ingest documents from data/documents/
        doc_files = list(DOCUMENTS_DIR.glob("*.*"))
        if not doc_files:
            print(f"[!] No document files found in {DOCUMENTS_DIR}")
            return

        print(f"\n[*] Ingesting {len(doc_files)} documents into project {project.id}...")
        for doc_path in doc_files:
            filename = doc_path.name
            file_bytes = doc_path.read_bytes()
            file_type = doc_path.suffix.lstrip(".").lower()

            # Check if document already exists
            res = await session.execute(
                select(Document).where(Document.project_id == project.id, Document.filename == filename)
            )
            existing_doc = res.scalar_one_or_none()
            if existing_doc and existing_doc.status == DocumentStatus.COMPLETED:
                print(f"  [✓] '{filename}' already ingested ({existing_doc.chunk_count} chunks).")
                continue

            if not existing_doc:
                doc = Document(
                    project_id=project.id,
                    filename=filename,
                    file_type=file_type,
                    file_size=len(file_bytes),
                    status=DocumentStatus.QUEUED,
                    chunking_config={"chunk_size": 400, "chunk_overlap": 40}
                )
                session.add(doc)
                await session.commit()
                await session.refresh(doc)
            else:
                doc = existing_doc

            print(f"  [→] Processing '{filename}' ({len(file_bytes)} bytes)...")
            processed_doc = await DocumentService.process_document_pipeline(
                document_id=doc.id,
                file_bytes=file_bytes,
                db=session,
                chunk_size=400,
                chunk_overlap=40
            )
            print(f"      Status: {processed_doc.status.value}, Chunks created: {processed_doc.chunk_count}")

        # 4. Demonstrate Sample RAG Query
        print("\n" + "=" * 60)
        print(" Testing End-to-End RAG Query")
        print("=" * 60)
        sample_question = "What is the work from home policy and what home office stipend is available?"
        print(f"Query Question: \"{sample_question}\"")
        
        rag_service = get_rag_service()
        response = await rag_service.answer(
            project_id=project.id,
            question=sample_question,
            top_k=3,
            similarity_threshold=0.0
        )

        print(f"\nModel: {response.model} (Latency: {response.latency_ms} ms)")
        print("\nGenerated Answer:")
        print("-" * 50)
        print(response.answer)
        print("-" * 50)
        print(f"\nRetrieved Citations ({len(response.sources)}):")
        for i, source in enumerate(response.sources, 1):
            print(f"  [{i}] Doc: {source.document} | Chunk #{source.chunk_index} | Score: {source.score}")
            print(f"      Preview: \"{source.text[:120]}...\"")

        print("\n[✓] Seed & RAG validation completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
