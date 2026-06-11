"""ORM tables for app.db (spec §9.1). All per-project rows carry project_id so the
portable per-project DB split in Milestone 3 is a data move, not a redesign."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    client_name: Mapped[str] = mapped_column(String)
    project_name: Mapped[str] = mapped_column(String)
    project_date: Mapped[str] = mapped_column(String)  # ISO date string
    maximo_version: Mapped[str] = mapped_column(String)
    folder_path: Mapped[str] = mapped_column(String, unique=True)
    branded_docx_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    filename: Mapped[str] = mapped_column(String)
    filepath: Mapped[str] = mapped_column(String)
    filetype: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime)
    user_timestamp_override: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_status: Mapped[str] = mapped_column(String)  # UPLOADED/EXTRACTING/EXTRACTED/PENDING/ERROR
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text_path: Mapped[str | None] = mapped_column(String, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def effective_timestamp(self) -> datetime:
        return self.user_timestamp_override or self.source_timestamp


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String)  # RUNNING/DONE/FAILED/CANCELLED
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources_used_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_sources_count: Mapped[int] = mapped_column(Integer, default=0)


class ProviderSettings(Base):
    __tablename__ = "provider_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # singleton row id=1
    provider: Mapped[str] = mapped_column(String, default="anthropic")
    model_id: Mapped[str] = mapped_column(String, default="claude-sonnet-4-6")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
