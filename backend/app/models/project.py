import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    guardrail_configs = relationship("ProjectGuardrailConfig", back_populates="project", cascade="all, delete-orphan")
    guardrail_logs = relationship("GuardrailExecutionLog", back_populates="project", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="project", cascade="all, delete-orphan")
    baselines = relationship("Baseline", back_populates="project", cascade="all, delete-orphan")
    threshold_config = relationship("ProjectThresholdConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")
