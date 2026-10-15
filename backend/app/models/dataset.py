import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan", order_by="desc(DatasetVersion.version)")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="versions")
    cases = relationship("EvaluationCase", back_populates="dataset_version", cascade="all, delete-orphan")

class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=True)
    expected_context: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    category: Mapped[str] = mapped_column(String, default="general", nullable=False)
    difficulty: Mapped[str] = mapped_column(String, default="medium", nullable=False)
    case_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset_version = relationship("DatasetVersion", back_populates="cases")
