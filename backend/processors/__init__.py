"""File-type classification and extraction dispatch (spec §8)."""
from pathlib import Path

TEXT_TYPES = {
    "pdf": "pdf",
    "docx": "docx",
    "txt": "plaintext",
    "md": "plaintext",
    "xlsx": "spreadsheet",
    "xls": "spreadsheet",
}

MEDIA_TYPES = {
    "mp3": "audio", "wav": "audio", "m4a": "audio", "ogg": "audio",
    "mp4": "video", "mov": "video", "webm": "video",
    "png": "image", "jpg": "image", "jpeg": "image", "webp": "image",
}


def classify(filename: str) -> str:
    """Return filetype key: pdf/docx/plaintext/spreadsheet/audio/video/image/unknown."""
    ext = Path(filename).suffix.lower().lstrip(".")
    return TEXT_TYPES.get(ext) or MEDIA_TYPES.get(ext) or "unknown"


def is_extractable(filetype: str) -> bool:
    return filetype in {"pdf", "docx", "plaintext", "spreadsheet"}


def embedded_date(filetype: str, filepath: str):
    """Date stored inside the file's own metadata (UTC), or None."""
    from processors import filedates

    return filedates.embedded_date(filetype, filepath)


def extract_text(filetype: str, filepath: str) -> tuple[str, int | None]:
    """Dispatch to the right processor. Returns (text, page_count or None).

    Raises on unreadable/corrupt files — caller sets ERROR status.
    """
    from processors import docx as docx_proc
    from processors import pdf as pdf_proc
    from processors import plaintext as plaintext_proc
    from processors import xlsx as xlsx_proc

    if filetype == "pdf":
        return pdf_proc.extract(filepath)
    if filetype == "docx":
        return docx_proc.extract(filepath), None
    if filetype == "plaintext":
        return plaintext_proc.extract(filepath), None
    if filetype == "spreadsheet":
        return xlsx_proc.extract(filepath), None
    raise ValueError(f"No processor for filetype '{filetype}'")
