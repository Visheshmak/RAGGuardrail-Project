from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID

from app.guardrails.base import GuardrailResult

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The user query or prompt")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of context chunks to retrieve")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity score threshold")
    enable_guardrails: bool = Field(True, description="Whether to evaluate input and output guardrails")

class SourceCitation(BaseModel):
    document: str = Field(..., description="Document filename")
    document_id: UUID = Field(..., description="Document unique identifier")
    chunk_id: UUID = Field(..., description="Chunk unique identifier")
    page: Optional[int] = Field(None, description="Page number if available")
    chunk_index: int = Field(..., description="Index of the chunk in document sequence")
    text: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(..., description="Similarity relevance score")

    model_config = ConfigDict(from_attributes=True)

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceCitation]
    model: str
    latency_ms: float
    blocked: bool = Field(False, description="Whether the response or query was blocked by guardrails")
    action: str = Field("allow", description="Guardrail action taken: allow, log, warning, block")
    guardrail_results: List[GuardrailResult] = Field(default_factory=list, description="Detailed guardrail check results")
