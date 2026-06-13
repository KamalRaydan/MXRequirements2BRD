"""Stage 2b — extract requirements from summarized sources (spec §12.4).

Map-reduce: sources are extracted in batches so a single call can't overflow the
output-token limit, then results are merged and de-duplicated. The LLM returns
RequirementDrafts (no IDs); assign_ids() then deterministically produces
BRD-{MODULE}-{NNN} identifiers (spec §7.5).
"""
import json
import re

import config
from models.pipeline import AnalysisDraft, AnalysisResult, Requirement, RequirementDraft, SummarizedSource
from services.llm_client import LLMClient


def _batch_sources(sources: list[SummarizedSource], budget: int) -> list[list[SummarizedSource]]:
    """Greedily group sources so each batch holds at most `budget` characters of
    content. A single oversized source still goes in its own batch."""
    batches: list[list[SummarizedSource]] = []
    current: list[SummarizedSource] = []
    size = 0
    for s in sources:
        length = len(s.content)
        if current and size + length > budget:
            batches.append(current)
            current, size = [], 0
        current.append(s)
        size += length
    if current:
        batches.append(current)
    return batches


def _dedup(drafts: list[RequirementDraft]) -> list[RequirementDraft]:
    """Reduce step: drop requirements that repeat across batches. Two drafts are
    "the same" when they share a module and a normalized title (case/whitespace
    insensitive). Keeps the first occurrence."""
    seen: set[tuple[str, str]] = set()
    unique: list[RequirementDraft] = []
    for d in drafts:
        key = (d.module, re.sub(r"\s+", " ", d.title).strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def assign_ids(drafts: list[RequirementDraft]) -> list[Requirement]:
    """Group by module, sort by sort_order (stable — list order breaks ties),
    then number BRD-{MODULE}-001, -002, ... per module."""
    by_module: dict[str, list[RequirementDraft]] = {}
    for draft in drafts:
        module = draft.module if draft.module in config.MODULE_CODES else "GENERAL"
        by_module.setdefault(module, []).append(draft)

    requirements: list[Requirement] = []
    for module in sorted(by_module):
        ordered = sorted(by_module[module], key=lambda d: d.sort_order)
        for n, draft in enumerate(ordered, start=1):
            requirements.append(Requirement(
                id=f"BRD-{module}-{n:03d}",
                module=module,
                title=draft.title,
                description=draft.description,
                requirement_type=draft.requirement_type,
                priority=draft.priority,
                source_ref=draft.source_ref,
                source_timestamp=draft.source_timestamp,
                notes=draft.notes,
            ))
    return requirements


def analyze(
    llm: LLMClient,
    sources: list[SummarizedSource],
    project_name: str,
    client_name: str,
    maximo_version_label: str,
    maximo_knowledge: str,
    section_titles: list[str],
    on_progress=None,
    on_batch=None,
) -> AnalysisResult:
    """Extract requirements across all sources via map-reduce.

    on_progress(chars): live character heartbeat within one batch's streaming call.
    on_batch(done, total, label): called as each batch finishes, for stage progress.
    """
    system = (config.PROMPTS_DIR / "analyzer_system.txt").read_text(encoding="utf-8").format(
        maximo_knowledge=maximo_knowledge,
        module_list=", ".join(config.MODULE_CODES),
    )
    user_template = (config.PROMPTS_DIR / "analyzer_user.txt").read_text(encoding="utf-8")

    batches = _batch_sources(sources, config.ANALYZE_BATCH_CHARS)

    # ---- Map: extract requirements from each batch independently ----
    all_drafts: list[RequirementDraft] = []
    modules_referenced: list[str] = []
    notes: list[str] = []
    for i, batch in enumerate(batches):
        sources_json = json.dumps([
            {"filename": s.filename, "timestamp": s.timestamp.isoformat(), "content": s.content}
            for s in batch
        ], indent=2)
        user = user_template.format(
            project_name=project_name,
            client_name=client_name,
            maximo_version_label=maximo_version_label,
            section_list=", ".join(section_titles),
            sources_json=sources_json,
        )
        draft: AnalysisDraft = llm.complete_json(
            messages=[{"role": "user", "content": user}],
            schema=AnalysisDraft,
            max_tokens=config.LLM_MAX_TOKENS_ANALYZE,
            system=system,
            on_progress=on_progress,
            cache_system=True,  # system+knowledge is identical across batches
        )
        # Offset sort_order so requirements keep batch (chronological) order globally,
        # while assign_ids still numbers them per module.
        for d in draft.requirements:
            d.sort_order += i * 10000
        all_drafts.extend(draft.requirements)
        for m in draft.modules_referenced:
            if m not in modules_referenced:
                modules_referenced.append(m)
        if draft.analysis_notes:
            notes.append(draft.analysis_notes)
        if on_batch:
            on_batch(i + 1, len(batches), ", ".join(s.filename for s in batch))

    # ---- Reduce: drop cross-batch duplicates, then assign deterministic IDs ----
    unique_drafts = _dedup(all_drafts)

    return AnalysisResult(
        requirements=assign_ids(unique_drafts),
        modules_referenced=modules_referenced,
        analysis_notes="\n\n".join(notes) or None,
    )
