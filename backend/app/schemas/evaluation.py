from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EvaluationRunCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Descriptive name for evaluation run")
    dataset_version_id: Optional[UUID] = Field(None, description="Dataset version to evaluate against")
    configuration_snapshot: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EvaluationCaseResultResponse(BaseModel):
    id: UUID
    evaluation_run_id: UUID
    evaluation_case_id: Optional[UUID] = None
    question: str
    expected_answer: Optional[str] = None
    actual_answer: Optional[str] = None
    retrieved_chunks: List[Dict[str, Any]]
    metrics: Dict[str, float]
    guardrail_results: List[Dict[str, Any]]
    passed: bool
    latency_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    dataset_version_id: Optional[UUID] = None
    name: str
    status: str
    total_cases: int
    completed_cases: int
    metrics: Dict[str, float]
    guardrail_summary: Dict[str, Any]
    configuration_snapshot: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BaselineCreate(BaseModel):
    evaluation_run_id: UUID = Field(..., description="ID of the evaluation run to promote as baseline")
    notes: Optional[str] = Field(None, description="Optional baseline notes/description")


class BaselineResponse(BaseModel):
    id: UUID
    project_id: UUID
    evaluation_run_id: UUID
    version: int
    is_active: bool
    configuration_snapshot: Dict[str, Any]
    metrics_snapshot: Dict[str, float]
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegressionResultResponse(BaseModel):
    id: UUID
    evaluation_run_id: UUID
    baseline_id: Optional[UUID] = None
    metric: str
    baseline_score: float
    current_score: float
    absolute_difference: float
    relative_difference: float
    allowed_regression: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectThresholdConfigUpdate(BaseModel):
    thresholds: Optional[Dict[str, Dict[str, float]]] = None
    block_on_critical_guardrail: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectThresholdConfigResponse(BaseModel):
    id: UUID
    project_id: UUID
    thresholds: Dict[str, Dict[str, float]]
    settings: Dict[str, Any]
    block_on_critical_guardrail: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReleaseDecisionResponse(BaseModel):
    decision: str = Field(..., description="Release decision: PASS, WARNING, BLOCK")
    passed: bool = Field(..., description="True if candidate passes release gate")
    reasons: List[Dict[str, Any]] = Field(default_factory=list, description="Reasons for gating decision")
    metrics_comparison: Optional[List[Dict[str, Any]]] = None
    baseline_version: Optional[int] = None
    evaluation_run_id: Optional[UUID] = None
