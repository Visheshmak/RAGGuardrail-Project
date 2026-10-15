from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GuardrailSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    LOG = "log"
    WARNING = "warning"
    BLOCK = "block"


class GuardrailTarget(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    BOTH = "both"


class GuardrailType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    PII_DETECTION = "pii_detection"
    PROMPT_LEAKAGE = "prompt_leakage"
    GROUNDING = "grounding"
    SAFETY = "safety"
    CUSTOM = "custom"


class GuardrailResult(BaseModel):
    guardrail: str = Field(..., description="Name or identifier of the guardrail")
    passed: bool = Field(..., description="Whether the check passed without critical safety violation")
    severity: GuardrailSeverity = Field(..., description="Assessed severity of the violation if failed")
    reason: str = Field(..., description="Explanation of the evaluation result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic or match data")


class BaseGuardrail(ABC):
    """Abstract base interface for all modular guardrails."""

    name: str = "base_guardrail"
    guardrail_type: GuardrailType = GuardrailType.CUSTOM
    description: str = "Base guardrail interface"
    target: GuardrailTarget = GuardrailTarget.BOTH

    @abstractmethod
    async def check(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """Evaluate the provided input/output text against guardrail rules."""
        pass
