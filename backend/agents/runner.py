"""Sequential pipeline orchestrator (spec §12). Runs as a FastAPI BackgroundTask
in a worker thread: opens its own DB session, publishes progress to the
ProgressBus, and updates the pipeline_runs row when finished or failed."""
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import config
from agents import analyzer, extractor, generator, summarizer
from db.database import SessionLocal
from db.models import PipelineRun, Project, Source
from services import docx_renderer, structure_extractor
from services.llm_client import LLMClient, LLMError
from services.progress_bus import bus


class PipelineCancelled(Exception):
    """Raised between stages when the user cancelled the run."""


def _progress(run_id: str, stage: str, message: str, percent: int, step: str | None = None) -> None:
    bus.publish(run_id, "progress", {
        "stage": stage, "step": step, "message": message, "percent": percent, "run_id": run_id,
    })


def _check_cancel(run_id: str) -> None:
    if bus.is_cancel_requested(run_id):
        raise PipelineCancelled()


def _load_structure(branded_docx_path: str | None = None) -> list[dict]:
    """Branded template headings win when a reference DOCX is set (spec §12.1)."""
    if branded_docx_path and Path(branded_docx_path).exists():
        return structure_extractor.extract_headings(branded_docx_path)
    template = json.loads((config.TEMPLATES_DIR / "brd_default_structure.json").read_text(encoding="utf-8"))
    return template["sections"]


def _load_knowledge(maximo_version: str) -> tuple[str, str]:
    """Returns (UI label, knowledge markdown)."""
    maximo_version = config.LEGACY_VERSION_KEYS.get(maximo_version, maximo_version)
    label, filename, _enabled = config.VERSION_MAP[maximo_version]
    return label, (config.KNOWLEDGE_DIR / filename).read_text(encoding="utf-8")


def run_pipeline(run_id: str, project_id: str, api_key: str, model_id: str,
                 provider: str = "anthropic") -> None:
    db = SessionLocal()
    try:
        run = db.get(PipelineRun, run_id)
        project = db.get(Project, project_id)

        # ---- Pre-flight (spec §12.1) ----
        version_label, knowledge = _load_knowledge(project.maximo_version)
        structure = _load_structure(project.branded_docx_path)
        llm = LLMClient(api_key=api_key, model_id=model_id, provider=provider)

        sources = (
            db.query(Source)
            .filter(Source.project_id == project_id, Source.processing_status == "EXTRACTED")
            .all()
        )
        sources.sort(key=lambda s: s.effective_timestamp)
        skipped = (
            db.query(Source)
            .filter(Source.project_id == project_id,
                    Source.processing_status.in_(["PENDING", "ERROR", "TRANSCRIBING", "EXTRACTING"]))
            .count()
        )
        run.sources_used_count = len(sources)
        run.skipped_sources_count = skipped
        db.commit()

        # ---- Stage 1: extraction (0–30%) ----
        extracted = []
        for i, source in enumerate(sources):
            _check_cancel(run_id)
            _progress(run_id, "extraction", f"Processing {source.filename}",
                      int(30 * (i + 1) / len(sources)))
            extracted.append(extractor.extract_source(source, project.folder_path))

        # ---- Stage 2a: summarization (30–55%) ----
        summarized = []
        for i, ext in enumerate(extracted):
            _check_cancel(run_id)
            percent = 30 + int(25 * (i + 1) / len(extracted))
            if ext.char_count > config.TOKEN_THRESHOLD:
                _progress(run_id, "analysis", f"Summarizing {ext.filename}", percent, step="summarizing")
            summarized.append(summarizer.summarize_if_needed(llm, ext))

        # ---- Stage 2b: analysis (55–75%) ----
        _check_cancel(run_id)
        _progress(run_id, "analysis", "Extracting requirements from sources", 60, step="extracting")
        analysis = analyzer.analyze(
            llm, summarized,
            project_name=project.project_name,
            client_name=project.client_name,
            maximo_version_label=version_label,
            maximo_knowledge=knowledge,
            section_titles=[s["title"] for s in structure],
        )
        _progress(run_id, "analysis",
                  f"Identified {len(analysis.requirements)} requirements", 75, step="extracting")

        # ---- Stage 3a: narrative generation (75–90%) ----
        _check_cancel(run_id)
        _progress(run_id, "generation", "Writing BRD narrative sections", 80)
        metadata = {
            "client_name": project.client_name,
            "project_name": project.project_name,
            "project_date": project.project_date,
            "maximo_version": project.maximo_version,
            "maximo_version_label": version_label,
        }
        appendix = sorted({s.filename for s in summarized})
        brd = generator.generate(llm, analysis, metadata, structure, appendix, knowledge)

        # ---- Stage 3b: render (90–100%) ----
        _check_cancel(run_id)
        _progress(run_id, "rendering", "Rendering Word document", 92)
        output_dir = Path(project.folder_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{run_id}.docx")
        docx_renderer.render(brd, output_path)

        run.status = "DONE"
        run.output_path = output_path
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        bus.publish(run_id, "done", {
            "stage": "done", "output_path": output_path, "percent": 100, "run_id": run_id,
        })

    except PipelineCancelled:
        run = db.get(PipelineRun, run_id)
        run.status = "CANCELLED"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        # stage "cancelled" lets the UI tell a cancel apart from a failure
        bus.publish(run_id, "error", {
            "stage": "cancelled", "message": "Generation cancelled", "percent": 0, "run_id": run_id,
        })
    except Exception as e:
        # User-safe message; full trace stays server-side only
        message = str(e) if isinstance(e, LLMError) else f"Pipeline failed: {type(e).__name__}: {e}"
        traceback.print_exc()
        try:
            run = db.get(PipelineRun, run_id)
            run.status = "FAILED"
            run.error_message = message
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            bus.publish(run_id, "error", {
                "stage": "failed", "message": message, "percent": 0, "run_id": run_id,
            })
    finally:
        db.close()
