"""Project CRUD (spec §10.2)."""
import re
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import config
from db.database import get_db
from db.models import PipelineRun, Project, Source
from models.project import ProjectCreate, ProjectOut, RunOut
from routes import api_error

router = APIRouter()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "project"


@router.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    if body.maximo_version not in config.VERSION_MAP:
        raise api_error(422, "INVALID_VERSION", f"Unknown Maximo version '{body.maximo_version}'")
    label, _file, enabled = config.VERSION_MAP[body.maximo_version]
    if not enabled:
        raise api_error(422, "VERSION_NOT_AVAILABLE", f"{label} support is coming soon")

    folder = body.folder_path or str(
        config.PROJECTS_DEFAULT_DIR / f"{_slug(body.client_name)}-{_slug(body.project_name)}"
    )
    if db.query(Project).filter(Project.folder_path == folder).first():
        raise api_error(409, "FOLDER_IN_USE", "Another project already uses this folder")

    # Create the project folder structure (spec §5.1)
    for sub in ("sources", "extracted", "output"):
        (Path(folder) / sub).mkdir(parents=True, exist_ok=True)

    project = Project(
        client_name=body.client_name,
        project_name=body.project_name,
        project_date=body.project_date,
        maximo_version=body.maximo_version,
        folder_path=folder,
    )
    db.add(project)
    db.commit()
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    source_count = db.query(Source).filter(Source.project_id == project_id).count()
    latest_run = (
        db.query(PipelineRun)
        .filter(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.started_at.desc())
        .first()
    )
    return {
        **ProjectOut.model_validate(project).model_dump(),
        "source_count": source_count,
        "latest_run": RunOut.model_validate(latest_run).model_dump() if latest_run else None,
    }


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    # Remove DB rows only — never delete the user's folder (spec §10.2)
    db.query(Source).filter(Source.project_id == project_id).delete()
    db.query(PipelineRun).filter(PipelineRun.project_id == project_id).delete()
    db.delete(project)
    db.commit()


@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
def list_runs(project_id: str, db: Session = Depends(get_db)):
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.started_at.desc())
        .all()
    )
