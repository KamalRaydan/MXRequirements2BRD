"""Embedded created/modified dates from document metadata.

Filesystem timestamps are unreliable — downloading an attachment from email
resets them to "now" — but PDF, DOCX, and XLSX files carry their own dates
inside the file, and those survive any transfer. Prefer last-modified (when
the content was finalized), fall back to created.
"""
import re
from datetime import datetime, timedelta, timezone


def embedded_date(filetype: str, filepath: str) -> datetime | None:
    """Best date stored inside the file itself (UTC), or None if unavailable.

    Never raises — unreadable metadata just means the caller falls back.
    """
    try:
        if filetype == "pdf":
            return _pdf_date(filepath)
        if filetype == "docx":
            return _docx_date(filepath)
        if filetype == "spreadsheet":
            return _xlsx_date(filepath)
    except Exception:
        return None
    return None


def _docx_date(filepath: str) -> datetime | None:
    import docx as python_docx

    props = python_docx.Document(filepath).core_properties
    return _to_utc(props.modified or props.created)


def _xlsx_date(filepath: str) -> datetime | None:
    import openpyxl

    workbook = openpyxl.load_workbook(filepath, read_only=True)
    try:
        props = workbook.properties
        return _to_utc(props.modified or props.created)
    finally:
        workbook.close()


def _pdf_date(filepath: str) -> datetime | None:
    import pymupdf

    with pymupdf.open(filepath) as doc:
        raw = doc.metadata.get("modDate") or doc.metadata.get("creationDate")
    return _parse_pdf_date(raw)


# PDF date string: D:YYYYMMDDHHmmSS+HH'mm' — everything after the year is optional
_PDF_DATE = re.compile(
    r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?"
)


def _parse_pdf_date(raw: str | None) -> datetime | None:
    match = _PDF_DATE.match(raw or "")
    if not match:
        return None
    year, month, day, hour, minute, second, sign, tz_h, tz_m = match.groups()
    parsed = datetime(
        int(year), int(month or 1), int(day or 1),
        int(hour or 0), int(minute or 0), int(second or 0),
        tzinfo=timezone.utc,
    )
    if sign in ("+", "-") and tz_h:
        offset = timedelta(hours=int(tz_h), minutes=int(tz_m or 0))
        local = timezone(offset if sign == "+" else -offset)
        parsed = parsed.replace(tzinfo=local).astimezone(timezone.utc)
    return parsed


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)  # OOXML dates are stored as UTC
    return value.astimezone(timezone.utc)
