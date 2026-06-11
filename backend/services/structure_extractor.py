"""Extract the heading structure from a branded reference DOCX (spec §12.1, Milestone 2).

The headings replace `brd_default_structure.json` as the section list for the
pipeline. Each heading is mapped to a canonical section id when its title matches
a known BRD section (so the renderer still knows where requirement tables and the
appendix go); unrecognised headings get a slug id and render as narrative sections.
"""
import re

import docx as python_docx

# Checked in order — first keyword found in the lowercased title wins. More
# specific phrases come first ("out of scope" before "scope", "non-functional"
# before "requirement").
_CANONICAL_KEYWORDS = [
    ("document control", "cover"),
    ("executive summary", "executive_summary"),
    ("background", "background"),
    ("objective", "background"),
    ("out of scope", "scope_out"),
    ("in scope", "scope_in"),
    ("scope", "scope"),
    ("assumption", "assumptions"),
    ("non-functional", "non_functional"),
    ("non functional", "non_functional"),
    ("integration", "integrations"),
    ("requirement", "requirements"),
    ("risk", "risks"),
    ("appendix", "appendix"),
    ("source documents", "appendix"),
]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "section"


def _section_id(title: str, used: set[str]) -> str:
    lowered = title.lower()
    for keyword, canonical in _CANONICAL_KEYWORDS:
        if keyword in lowered and canonical not in used:
            return canonical
    base = _slug(title)
    candidate, n = base, 1
    while candidate in used:
        n += 1
        candidate = f"{base}_{n}"
    return candidate


def _heading_level(style_name: str) -> int | None:
    """'Heading 1' -> 1; returns None for non-heading styles or levels deeper than 3."""
    match = re.fullmatch(r"heading (\d+)", style_name.lower())
    if match and 1 <= int(match.group(1)) <= 3:
        return int(match.group(1))
    return None


def extract_headings(filepath: str) -> list[dict]:
    """Returns sections shaped like brd_default_structure.json entries.

    Raises ValueError if the document has no Heading 1–3 paragraphs.
    """
    document = python_docx.Document(filepath)
    sections: list[dict] = []
    used_ids: set[str] = set()

    for para in document.paragraphs:
        title = para.text.strip()
        if not title:
            continue
        level = _heading_level(para.style.name if para.style else "")
        if level is None:
            continue
        section_id = _section_id(title, used_ids)
        used_ids.add(section_id)
        # required=True so the renderer never drops a branded heading
        sections.append({"id": section_id, "title": title, "level": level, "required": True})

    if not sections:
        raise ValueError("No headings (Heading 1–3) found in the branded document")
    return sections
