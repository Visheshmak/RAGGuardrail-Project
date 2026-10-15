from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class EvaluationCaseBase(BaseModel):
    question: str = Field(..., min_length=1, description="The evaluation test question")
    expected_answer: Optional[str] = Field(None, description="Ground truth reference answer")
    expected_context: Optional[List[str]] = Field(default_factory=list, description="Target document names or context references")
    category: str = Field("general", description="Evaluation category (e.g. policy, technical, security)")
    difficulty: str = Field("medium", description="Question difficulty: easy, medium, hard")
    case_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata tags or notes")

class EvaluationCaseCreate(EvaluationCaseBase):
    pass

class EvaluationCaseResponse(EvaluationCaseBase):
    id: UUID
    dataset_version_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DatasetVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    version: int
    case_count: int
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class DatasetCreate(DatasetBase):
    initial_cases: Optional[List[EvaluationCaseCreate]] = None

class DatasetResponse(DatasetBase):
    id: UUID
    project_id: UUID
    versions: List[DatasetVersionResponse] = []
    latest_version: Optional[int] = None
    total_cases: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CreateVersionRequest(BaseModel):
    description: Optional[str] = None
    cases: List[EvaluationCaseCreate] = Field(..., min_length=1)

class DatasetStatistics(BaseModel):
    total_cases: int
    categories: Dict[str, int]
    difficulties: Dict[str, int]
    has_expected_answer_count: int
    has_expected_context_count: int

class DatasetUploadSummary(BaseModel):
    dataset_id: UUID
    version_id: UUID
    version: int
    total_parsed: int
    valid_cases_added: int
    duplicate_count: int
    skipped_empty_rows: int
    warnings: List[str] = []
    errors: List[str] = []
