"""Stage 1 — read extracted text for each eligible source (spec §12.2).

Prefers the sidecar cache in extracted/{source_id}.txt; re-extracts only if the
sidecar is missing or empty.
"""
from pathlib import Path

import processors
from db.models import Source
from models.pipeline import ExtractedSource


def extract_source(source: Source, project_folder: str) -> ExtractedSource:
    sidecar = Path(project_folder) / "extracted" / f"{source.id}.txt"

    if sidecar.exists() and sidecar.stat().st_size > 0:
        text = sidecar.read_text(encoding="utf-8")
        page_count = None
    else:
        result = processors.extract_text(source.filetype, source.filepath)
        text, page_count = result
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(text, encoding="utf-8")

    return ExtractedSource(
        source_id=source.id,
        filename=source.filename,
        timestamp=source.effective_timestamp,
        raw_text=text,
        char_count=len(text),
        page_count=page_count,
    )
