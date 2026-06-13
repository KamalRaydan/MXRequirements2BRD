"""Request/response schemas for project and source routes (spec §10)."""
from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    client_name: str
    project_name: str
    project_date: str  # ISO date
    maximo_version: str
    folder_path: str | None = None  # defaults to ~/MaximoBRD/{client}-{project}


class ProjectOut(BaseModel):
    id: str
    client_name: str
    project_name: str
    project_date: str
    maximo_version: str
    folder_path: str
    branded_docx_path: str | None
    created_at: datetime
    is_custom_folder: bool = False  # True if the user chose the folder; controls delete cleanup wording

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: str
    filename: str
    filetype: str
    file_size_bytes: int
    source_timestamp: datetime
    user_timestamp_override: datetime | None
    processing_status: str
    error_message: str | None
    char_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceTextOut(BaseModel):
    text: str
    char_count: int


class SourcePatch(BaseModel):
    user_timestamp_override: datetime | None = None


class RunOut(BaseModel):
    id: str
    project_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    output_path: str | None
    error_message: str | None
    sources_used_count: int
    skipped_sources_count: int

    model_config = {"from_attributes": True}
