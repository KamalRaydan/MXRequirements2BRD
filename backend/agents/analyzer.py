"""Stage 2b — extract requirements from summarized sources (spec §12.4).

The LLM returns RequirementDrafts (no IDs); assign_ids() then deterministically
produces BRD-{MODULE}-{NNN} identifiers (spec §7.5).
"""
import json

import config
from models.pipeline import AnalysisDraft, AnalysisResult, Requirement, RequirementDraft, SummarizedSource
from services.llm_client import LLMClient


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
) -> AnalysisResult:
    system = (config.PROMPTS_DIR / "analyzer_system.txt").read_text(encoding="utf-8").format(
        maximo_knowledge=maximo_knowledge,
        module_list=", ".join(config.MODULE_CODES),
    )

    sources_json = json.dumps([
        {"filename": s.filename, "timestamp": s.timestamp.isoformat(), "content": s.content}
        for s in sources
    ], indent=2)

    user = (config.PROMPTS_DIR / "analyzer_user.txt").read_text(encoding="utf-8").format(
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
    )

    return AnalysisResult(
        requirements=assign_ids(draft.requirements),
        modules_referenced=draft.modules_referenced,
        analysis_notes=draft.analysis_notes,
    )
