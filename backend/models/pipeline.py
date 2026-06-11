"""Pydantic contracts passed between pipeline stages (spec §9.2)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RequirementDraft(BaseModel):
    """A requirement as the LLM returns it — before BRD IDs are assigned."""

    module: str
    title: str
    description: str
    requirement_type: Literal["functional", "non_functional", "configuration", "integration"]
    priority: Literal["high", "medium", "low"]
    source_ref: str  # filename only
    source_timestamp: str  # ISO 8601
    sort_order: int
    notes: str | None = None


class Requirement(BaseModel):
    """A requirement after deterministic ID assignment (BRD-WO-001, ...)."""

    id: str
    module: str
    title: str
    description: str
    requirement_type: str
    priority: str
    source_ref: str
    source_timestamp: str
    notes: str | None = None


class ExtractedSource(BaseModel):
    source_id: str
    filename: str
    timestamp: datetime
    raw_text: str
    char_count: int
    page_count: int | None = None


class SummarizedSource(BaseModel):
    source_id: str
    filename: str
    timestamp: datetime
    content: str  # full text or summary
    was_summarized: bool


class AnalysisDraft(BaseModel):
    """Analyzer LLM output schema (drafts, no IDs yet)."""

    requirements: list[RequirementDraft]
    modules_referenced: list[str]
    analysis_notes: str | None = None


class AnalysisResult(BaseModel):
    requirements: list[Requirement]
    modules_referenced: list[str]
    analysis_notes: str | None = None


class NarrativeSection(BaseModel):
    section_id: str  # matches brd_default_structure id
    title: str
    body: str  # plain text, paragraphs separated by \n\n


class NarrativeSet(BaseModel):
    """Generator LLM output schema."""

    narratives: list[NarrativeSection]


class BRDDocument(BaseModel):
    project_metadata: dict
    structure: list[dict]  # ordered sections from the template
    narratives: list[NarrativeSection]
    requirements: list[Requirement]
    appendix_sources: list[str]
