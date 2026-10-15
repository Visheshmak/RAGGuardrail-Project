from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.guardrails.base import (
    GuardrailAction,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


class GuardrailCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to evaluate (prompt or answer)")
    target: GuardrailTarget = Field(GuardrailTarget.INPUT, description="Whether checking input or output")
    retrieved_chunks: Optional[List[str]] = Field(None, description="Context chunks for grounding checks")
    system_prompt: Optional[str] = Field(None, description="System prompt for leakage verification")
    custom_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom thresholds or regexes")


class GuardrailCheckResponse(BaseModel):
    passed: bool
    action: GuardrailAction
    blocked_reason: Optional[str] = None
    max_severity: Optional[GuardrailSeverity] = None
    results: List[GuardrailResult]
    latency_ms: float
    target: GuardrailTarget


class ProjectGuardrailConfigCreate(BaseModel):
    guardrail_type: str
    name: str
    description: Optional[str] = None
    target: str = "both"
    is_enabled: bool = True
    severity_override: Optional[str] = None
    action_override: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ProjectGuardrailConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    target: Optional[str] = None
    severity_override: Optional[str] = None
    action_override: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ProjectGuardrailConfigResponse(BaseModel):
    id: UUID
    project_id: UUID
    guardrail_type: str
    name: str
    description: Optional[str] = None
    is_enabled: bool
    target: str
    severity_override: Optional[str] = None
    action_override: Optional[str] = None
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuardrailExecutionLogResponse(BaseModel):
    id: UUID
    project_id: UUID
    evaluation_case_id: Optional[UUID] = None
    guardrail_name: str
    target: str
    passed: bool
    severity: str
    action_taken: str
    reason: str
    execution_metadata: Dict[str, Any]
    latency_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
