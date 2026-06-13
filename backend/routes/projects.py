"""Project CRUD + branded template upload (spec §10.2)."""
import re
import shutil
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

import config
from db.database import get_db
from db.models import PipelineRun, Project, Source
from models.project import ProjectCreate, ProjectOut, RunOut
from routes import api_error
from services import structure_extractor

router = APIRouter()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "project"


# Subfolders this app creates and owns inside every project folder.
APP_SUBFOLDERS = ("sources", "extracted", "output", "branding")


def _default_folder(client_name: str, project_name: str) -> str:
    """The folder we auto-create when the user doesn't choose their own."""
    return str(config.PROJECTS_DEFAULT_DIR / f"{_slug(client_name)}-{_slug(project_name)}")


def _is_auto_folder(project) -> bool:
    """True when the project's folder is the one we generated for it (the user
    left the folder blank). In that case the whole folder belongs to the app, so
    it is safe to remove it on delete. A folder the user picked is left alone."""
    return Path(project.folder_path) == Path(_default_folder(project.client_name, project.project_name))


@router.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    if body.maximo_version not in config.VERSION_MAP:
        raise api_error(422, "INVALID_VERSION", f"Unknown Maximo version '{body.maximo_version}'")
    label, _file, enabled = config.VERSION_MAP[body.maximo_version]
    if not enabled:
        raise api_error(422, "VERSION_NOT_AVAILABLE", f"{label} support is coming soon")

    folder = body.folder_path or _default_folder(body.client_name, body.project_name)
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
    project.is_custom_folder = not _is_auto_folder(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    for p in projects:
        p.is_custom_folder = not _is_auto_folder(p)  # tells the UI whether delete removes the folder
    return projects


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    project.is_custom_folder = not _is_auto_folder(project)
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

    # Remove the files this app created for the project: the subfolders it makes
    # and everything inside them. Files the user put elsewhere are untouched.
    folder = Path(project.folder_path)
    for sub in APP_SUBFOLDERS:
        shutil.rmtree(folder / sub, ignore_errors=True)

    # If we auto-generated this folder, the whole thing is ours, so remove it too
    # — but only if nothing unexpected is left inside. A folder the user chose is
    # always kept, even when empty.
    if _is_auto_folder(project) and folder.exists() and not any(folder.iterdir()):
        folder.rmdir()

    db.query(Source).filter(Source.project_id == project_id).delete()
    db.query(PipelineRun).filter(PipelineRun.project_id == project_id).delete()
    db.delete(project)
    db.commit()


@router.put("/projects/{project_id}/branding")
async def upload_branding(project_id: str, file: UploadFile, db: Session = Depends(get_db)):
    """Branded reference DOCX whose headings replace the default BRD structure
    in the pipeline (spec §10.2, Milestone 2)."""
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    if not file.filename.lower().endswith(".docx"):
        raise api_error(422, "INVALID_TEMPLATE", "The branded template must be a .docx file")

    branding_dir = Path(project.folder_path) / "branding"
    branding_dir.mkdir(parents=True, exist_ok=True)
    reference = branding_dir / "reference.docx"

    async with aiofiles.open(reference, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            await out.write(chunk)

    try:
        headings = structure_extractor.extract_headings(str(reference))
    except Exception as e:
        reference.unlink(missing_ok=True)
        if project.branded_docx_path == str(reference):
            project.branded_docx_path = None
            db.commit()
        raise api_error(422, "INVALID_TEMPLATE",
                        f"Could not read headings from this document: {e}")

    project.branded_docx_path = str(reference)
    db.commit()
    return {"branded_docx_path": project.branded_docx_path, "headings": headings}


@router.get("/projects/{project_id}/branding")
def get_branding(project_id: str, db: Session = Depends(get_db)):
    """Heading preview for the currently stored branded template (if any)."""
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    if not project.branded_docx_path or not Path(project.branded_docx_path).exists():
        return {"branded_docx_path": None, "headings": []}
    headings = structure_extractor.extract_headings(project.branded_docx_path)
    return {"branded_docx_path": project.branded_docx_path, "headings": headings}


@router.delete("/projects/{project_id}/branding", status_code=204)
def delete_branding(project_id: str, db: Session = Depends(get_db)):
    """Revert to the default BRD structure (removes the stored reference file)."""
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")
    if project.branded_docx_path:
        Path(project.branded_docx_path).unlink(missing_ok=True)
        project.branded_docx_path = None
        db.commit()


@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
def list_runs(project_id: str, db: Session = Depends(get_db)):
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.project_id == project_id)
        .order_by(PipelineRun.started_at.desc())
        .all()
    )
