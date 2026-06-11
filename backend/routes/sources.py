"""Source upload, listing, deletion, timestamp override (spec §10.3, §8)."""
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile
from sqlalchemy.orm import Session

import config
import processors
from db.database import SessionLocal, get_db
from db.models import Project, Source
from models.project import SourceOut, SourcePatch
from routes import api_error

router = APIRouter()

_CHUNK = 1024 * 1024  # 1 MB


def _unique_filename(folder: Path, filename: str) -> str:
    """workshop.pdf -> workshop_1.pdf on collision (spec §10.3)."""
    candidate = filename
    n = 0
    while (folder / candidate).exists():
        n += 1
        stem, suffix = Path(filename).stem, Path(filename).suffix
        candidate = f"{stem}_{n}{suffix}"
    return candidate


def _extract_in_background(source_id: str) -> None:
    """Runs in a worker thread after upload: EXTRACTING -> EXTRACTED or ERROR."""
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        project = db.get(Project, source.project_id)
        try:
            text, _pages = processors.extract_text(source.filetype, source.filepath)
            if not text:
                raise ValueError("No text could be extracted from this file")
            sidecar = Path(project.folder_path) / "extracted" / f"{source.id}.txt"
            sidecar.parent.mkdir(parents=True, exist_ok=True)
            sidecar.write_text(text, encoding="utf-8")
            source.processing_status = "EXTRACTED"
            source.extracted_text_path = str(sidecar)
            source.char_count = len(text)
            source.error_message = None
        except Exception as e:
            source.processing_status = "ERROR"
            source.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/projects/{project_id}/sources/upload", status_code=201, response_model=SourceOut)
async def upload_source(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    source_timestamp: str | None = Form(default=None),
    user_timestamp_override: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")

    sources_dir = Path(project.folder_path) / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    filename = _unique_filename(sources_dir, Path(file.filename).name)
    filepath = sources_dir / filename

    # Stream to disk in chunks — never buffer the whole file in RAM (spec §10.3)
    size = 0
    async with aiofiles.open(filepath, "wb") as out:
        while chunk := await file.read(_CHUNK):
            size += len(chunk)
            if size > config.MAX_UPLOAD_BYTES:
                await out.close()
                filepath.unlink(missing_ok=True)
                raise api_error(413, "FILE_TOO_LARGE",
                                f"File exceeds the {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")
            await out.write(chunk)

    filetype = processors.classify(filename)
    if processors.is_extractable(filetype):
        status, error = "EXTRACTING", None
    elif filetype == "unknown":
        status, error = "ERROR", "Unsupported file type"
    else:
        status, error = "PENDING", None  # audio/video/image — Milestone 5

    timestamp = (
        datetime.fromisoformat(source_timestamp.replace("Z", "+00:00"))
        if source_timestamp else datetime.now(timezone.utc)
    )
    override = (
        datetime.fromisoformat(user_timestamp_override.replace("Z", "+00:00"))
        if user_timestamp_override else None
    )

    source = Source(
        project_id=project_id,
        filename=filename,
        filepath=str(filepath),
        filetype=filetype,
        file_size_bytes=size,
        source_timestamp=timestamp,
        user_timestamp_override=override,
        processing_status=status,
        error_message=error,
    )
    db.add(source)
    db.commit()

    if status == "EXTRACTING":
        background_tasks.add_task(_extract_in_background, source.id)

    return source


@router.get("/projects/{project_id}/sources", response_model=list[SourceOut])
def list_sources(project_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Source)
        .filter(Source.project_id == project_id)
        .order_by(Source.created_at.asc())
        .all()
    )


@router.delete("/projects/{project_id}/sources/{source_id}", status_code=204)
def delete_source(project_id: str, source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source or source.project_id != project_id:
        raise api_error(404, "NOT_FOUND", "Source not found")
    Path(source.filepath).unlink(missing_ok=True)
    if source.extracted_text_path:
        Path(source.extracted_text_path).unlink(missing_ok=True)
    db.delete(source)
    db.commit()


@router.patch("/projects/{project_id}/sources/{source_id}", response_model=SourceOut)
def patch_source(project_id: str, source_id: str, body: SourcePatch, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source or source.project_id != project_id:
        raise api_error(404, "NOT_FOUND", "Source not found")
    source.user_timestamp_override = body.user_timestamp_override
    db.commit()
    return source
