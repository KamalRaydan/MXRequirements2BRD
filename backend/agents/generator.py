"""Stage 3a — write the BRD narrative sections (spec §12.5)."""
import json

import config
from models.pipeline import AnalysisResult, BRDDocument, NarrativeSet
from services.llm_client import LLMClient


def generate(
    llm: LLMClient,
    analysis: AnalysisResult,
    project_metadata: dict,
    structure: list[dict],
    appendix_sources: list[str],
    maximo_knowledge: str,
) -> BRDDocument:
    system = (config.PROMPTS_DIR / "generator_system.txt").read_text(encoding="utf-8").format(
        maximo_knowledge=maximo_knowledge,
    )
    user = (config.PROMPTS_DIR / "generator_user.txt").read_text(encoding="utf-8").format(
        metadata_json=json.dumps(project_metadata),
        structure_json=json.dumps(structure),
        requirements_json=json.dumps([r.model_dump() for r in analysis.requirements], indent=2),
    )

    narrative_set: NarrativeSet = llm.complete_json(
        messages=[{"role": "user", "content": user}],
        schema=NarrativeSet,
        max_tokens=config.LLM_MAX_TOKENS_GENERATE,
        system=system,
    )

    return BRDDocument(
        project_metadata=project_metadata,
        structure=structure,
        narratives=narrative_set.narratives,
        requirements=analysis.requirements,
        appendix_sources=appendix_sources,
    )
