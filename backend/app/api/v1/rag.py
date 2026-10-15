from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project
from app.schemas.rag import QueryRequest, QueryResponse
from app.api.deps import get_current_user
from app.rag.rag_service import get_rag_service

from app.guardrails.base import GuardrailAction
from app.services.guardrail_service import GuardrailService

router = APIRouter()

@router.post("/{project_id}/query", response_model=QueryResponse)
async def query_rag_pipeline(
    project_id: UUID,
    query_in: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project access
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this project")

    rag_service = get_rag_service()
    pipeline = await GuardrailService.get_pipeline_for_project(project_id, db)

    # 1. Evaluate Input Guardrails
    if query_in.enable_guardrails:
        input_check = await pipeline.check_input(query_in.question)
        await GuardrailService.log_execution_results(
            project_id=project_id,
            results=input_check.results,
            target="input",
            policy=pipeline.policy,
            latency_ms=input_check.latency_ms,
            db=db
        )
        if input_check.action == GuardrailAction.BLOCK:
            return QueryResponse(
                question=query_in.question,
                answer=f"I cannot process this request because it violated safety policies: {input_check.blocked_reason}",
                sources=[],
                model=rag_service.llm_provider.model_name,
                latency_ms=input_check.latency_ms,
                blocked=True,
                action=input_check.action.value,
                guardrail_results=input_check.results
            )

    # 2. Execute RAG Retrieval & Generation
    response = await rag_service.answer(
        project_id=project_id,
        question=query_in.question,
        top_k=query_in.top_k,
        similarity_threshold=query_in.similarity_threshold
    )

    # 3. Evaluate Output Guardrails
    if query_in.enable_guardrails:
        output_check = await pipeline.check_output(
            text=response.answer,
            retrieved_chunks=response.sources
        )
        await GuardrailService.log_execution_results(
            project_id=project_id,
            results=output_check.results,
            target="output",
            policy=pipeline.policy,
            latency_ms=output_check.latency_ms,
            db=db
        )

        all_results = (input_check.results if query_in.enable_guardrails else []) + output_check.results
        overall_action, blocked_reason, _ = pipeline.policy.evaluate_results(all_results)

        if output_check.action == GuardrailAction.BLOCK:
            return QueryResponse(
                question=query_in.question,
                answer=f"Generated response was blocked by guardrails: {output_check.blocked_reason}",
                sources=response.sources,
                model=response.model,
                latency_ms=response.latency_ms + output_check.latency_ms,
                blocked=True,
                action=overall_action.value,
                guardrail_results=all_results
            )

        response.guardrail_results = all_results
        response.action = overall_action.value
        response.blocked = False

    return response
