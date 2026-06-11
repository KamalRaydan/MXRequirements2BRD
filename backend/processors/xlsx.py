"""Spreadsheet text extraction via openpyxl (xlsx; legacy xls not supported in MVP)."""
from pathlib import Path

import openpyxl


def extract(filepath: str) -> str:
    if Path(filepath).suffix.lower() == ".xls":
        raise ValueError("Legacy .xls files are not supported yet — please re-save as .xlsx")

    workbook = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    parts: list[str] = []
    try:
        for sheet in workbook.worksheets:
            parts.append(f"=== Sheet: {sheet.title} ===")
            for row in sheet.iter_rows(values_only=True):
                cells = ["" if v is None else str(v).strip() for v in row]
                if any(cells):
                    parts.append(" | ".join(cells))
    finally:
        workbook.close()
    return "\n".join(parts).strip()
