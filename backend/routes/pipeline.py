"""Generate, SSE progress stream, run status, download (spec §10.5, §11)."""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from agents.runner import run_pipeline
from db.database import get_db
from db.models import PipelineRun, Project, Source
from models.project import RunOut
from routes import api_error
from services import keystore
from services.progress_bus import bus

router = APIRouter()

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/projects/{project_id}/generate", status_code=202)
def generate(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise api_error(404, "NOT_FOUND", "Project not found")

    from db.models import ProviderSettings
    settings = db.get(ProviderSettings, 1)
    provider = settings.provider if settings else "anthropic"
    model_id = settings.model_id if settings else "claude-sonnet-4-6"

    api_key = keystore.get_api_key(provider)
    if not api_key:
        raise api_error(400, "NO_KEY", "Configure your AI provider in Settings first")

    extracted_count = (
        db.query(Source)
        .filter(Source.project_id == project_id, Source.processing_status == "EXTRACTED")
        .count()
    )
    if extracted_count == 0:
        raise api_error(400, "NO_SOURCES", "At least one source must finish extraction before generating")

    run = PipelineRun(project_id=project_id, status="RUNNING")
    db.add(run)
    db.commit()

    bus.start_run(run.id)
    background_tasks.add_task(run_pipeline, run.id, project_id, api_key, model_id, provider)
    return {"run_id": run.id, "status": "RUNNING"}


@router.get("/pipeline/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(PipelineRun, run_id)
    if not run:
        raise api_error(404, "NOT_FOUND", "Run not found")
    return run


@router.post("/pipeline/{run_id}/cancel", status_code=202)
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    """Sets the cancel flag; the pipeline checks it between stages (spec §10.5)."""
    run = db.get(PipelineRun, run_id)
    if not run:
        raise api_error(404, "NOT_FOUND", "Run not found")
    if run.status != "RUNNING":
        raise api_error(409, "NOT_RUNNING", f"Run already finished ({run.status})")
    bus.request_cancel(run_id)
    return {"run_id": run_id, "status": "CANCELLING"}


@router.get("/pipeline/{run_id}/stream")
async def stream_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(PipelineRun, run_id)
    if not run:
        raise api_error(404, "NOT_FOUND", "Run not found")

    # If the server restarted and lost in-memory events, synthesize a final event
    if not bus.has_run(run_id) and run.status != "RUNNING":
        bus.start_run(run_id)
        if run.status == "DONE":
            bus.publish(run_id, "done", {"stage": "done", "output_path": run.output_path,
                                         "percent": 100, "run_id": run_id})
        elif run.status == "CANCELLED":
            bus.publish(run_id, "error", {"stage": "cancelled", "message": "Generation cancelled",
                                          "percent": 0, "run_id": run_id})
        else:
            bus.publish(run_id, "error", {"stage": "failed",
                                          "message": run.error_message or "Run failed",
                                          "percent": 0, "run_id": run_id})

    async def event_stream():
        index = 0
        while True:
            events = bus.events_since(run_id, index)
            for event in events:
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
            index += len(events)
            if bus.is_finished(run_id) and not bus.events_since(run_id, index):
                return  # stream closes after done/error (spec §11)
            await asyncio.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/pipeline/{run_id}/download")
def download(run_id: str, db: Session = Depends(get_db)):
    run = db.get(PipelineRun, run_id)
    if not run:
        raise api_error(404, "NOT_FOUND", "Run not found")
    if run.status != "DONE" or not run.output_path or not Path(run.output_path).exists():
        raise api_error(400, "NOT_READY", "This run has no completed BRD to download")

    project = db.get(Project, run.project_id)
    nice_name = f"BRD - {project.client_name} - {project.project_name} (DRAFT).docx"
    return FileResponse(run.output_path, media_type=_DOCX_MIME, filename=nice_name)
