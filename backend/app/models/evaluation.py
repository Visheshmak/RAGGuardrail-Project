import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, Float, Text, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False, index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # e.g. accuracy, faithfulness, recall, safety
    guardrail_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="evaluation_runs")
    dataset_version = relationship("DatasetVersion")
    case_results = relationship("EvaluationCaseResult", back_populates="evaluation_run", cascade="all, delete-orphan")
    regression_results = relationship("RegressionResult", back_populates="evaluation_run", cascade="all, delete-orphan")
    baselines = relationship("Baseline", back_populates="evaluation_run", cascade="all, delete-orphan")


class EvaluationCaseResult(Base):
    __tablename__ = "evaluation_case_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieved_chunks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    guardrail_results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    evaluation_run = relationship("EvaluationRun", back_populates="case_results")
    evaluation_case = relationship("EvaluationCase")


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    project = relationship("Project", back_populates="baselines")
    evaluation_run = relationship("EvaluationRun", back_populates="baselines")
    regression_results = relationship("RegressionResult", back_populates="baseline")


class RegressionResult(Base):
    __tablename__ = "regression_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("baselines.id", ondelete="SET NULL"), nullable=True, index=True)
    metric: Mapped[str] = mapped_column(String, nullable=False, index=True)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    current_score: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_difference: Mapped[float] = mapped_column(Float, nullable=False)  # current - baseline
    relative_difference: Mapped[float] = mapped_column(Float, nullable=False)  # (current - baseline) / baseline
    allowed_regression: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)  # PASS, WARNING, FAIL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    evaluation_run = relationship("EvaluationRun", back_populates="regression_results")
    baseline = relationship("Baseline", back_populates="regression_results")


class ProjectThresholdConfig(Base):
    __tablename__ = "project_threshold_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    block_on_critical_guardrail: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="threshold_config")
