"""Rendered BRD has requirement tables, DRAFT watermark, named styles (spec §17.1)."""
import json

import docx as python_docx

import config
from models.pipeline import BRDDocument, NarrativeSection, Requirement
from services import docx_renderer


def _sample_brd() -> BRDDocument:
    structure = json.loads(
        (config.TEMPLATES_DIR / "brd_default_structure.json").read_text()
    )["sections"]
    return BRDDocument(
        project_metadata={
            "client_name": "Acme Corp",
            "project_name": "EAM Upgrade",
            "project_date": "2026-06-01",
            "maximo_version": "mas-9",
            "maximo_version_label": "MAS 9.x",
        },
        structure=structure,
        narratives=[
            NarrativeSection(section_id="executive_summary", title="Executive Summary",
                             body="First paragraph.\n\nSecond paragraph."),
            NarrativeSection(section_id="risks", title="Implementation Risks",
                             body="Risk one."),
        ],
        requirements=[
            Requirement(id="BRD-WO-001", module="WO", title="Auto-close work orders",
                        description="Close WOs after 30 days", requirement_type="functional",
                        priority="high", source_ref="workshop.pdf",
                        source_timestamp="2026-05-15T09:00:00Z"),
            Requirement(id="BRD-ASSET-001", module="ASSET", title="Criticality ratings",
                        description="All assets rated 1-5", requirement_type="configuration",
                        priority="medium", source_ref="assets.xlsx",
                        source_timestamp="2026-05-16T09:00:00Z"),
        ],
        appendix_sources=["workshop.pdf", "assets.xlsx"],
    )


def test_render_output(tmp_path):
    out = str(tmp_path / "brd.docx")
    docx_renderer.render(_sample_brd(), out)
    document = python_docx.Document(out)

    # One module table per module + the Document Control table
    assert len(document.tables) == 3

    # Requirement IDs present in table cells
    all_cell_text = "\n".join(
        cell.text for table in document.tables for row in table.rows for cell in row.cells
    )
    assert "BRD-WO-001" in all_cell_text
    assert "BRD-ASSET-001" in all_cell_text

    # DRAFT watermark present in the page header XML
    header_xml = document.sections[0].header.paragraphs[0]._p.xml
    assert "DRAFT" in header_xml

    # Headings use named styles; narrative paragraphs use Normal
    styles_used = {p.style.name for p in document.paragraphs}
    assert "Heading 1" in styles_used
    assert "Normal" in styles_used

    # Optional empty sections (non_functional, integrations) are skipped
    headings = [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]
    assert "Non-Functional Requirements" not in headings
    assert "Executive Summary" in headings
