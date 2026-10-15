import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, Float, Text, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ProjectGuardrailConfig(Base):
    __tablename__ = "project_guardrail_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    guardrail_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target: Mapped[str] = mapped_column(String, default="both", nullable=False)  # input, output, both
    severity_override: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action_override: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="guardrail_configs")


class GuardrailExecutionLog(Base):
    __tablename__ = "guardrail_execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    guardrail_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target: Mapped[str] = mapped_column(String, nullable=False)  # input, output, both
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)  # low, medium, high, critical
    action_taken: Mapped[str] = mapped_column(String, nullable=False, index=True)  # allow, log, warning, block
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    execution_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    project = relationship("Project", back_populates="guardrail_logs")
    evaluation_case = relationship("EvaluationCase")
