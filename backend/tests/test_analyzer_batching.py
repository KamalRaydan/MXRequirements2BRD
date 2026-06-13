"""Map-reduce analysis: sources are batched under a char budget, then results are
merged and de-duplicated (spec §12.4)."""
from datetime import datetime, timezone

from agents.analyzer import _batch_sources, _dedup
from models.pipeline import RequirementDraft, SummarizedSource


def _source(name: str, content: str) -> SummarizedSource:
    return SummarizedSource(
        source_id=name, filename=name, timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc),
        content=content, was_summarized=False,
    )


def _draft(module: str, title: str) -> RequirementDraft:
    return RequirementDraft(
        module=module, title=title, description="d",
        requirement_type="functional", priority="high",
        source_ref="f.txt", source_timestamp="2026-05-01T00:00:00Z", sort_order=1,
    )


def test_batches_group_under_budget():
    sources = [_source(f"s{i}", "x" * 40) for i in range(5)]
    # budget fits two 40-char sources per batch (80), so 5 sources -> 3 batches
    batches = _batch_sources(sources, budget=80)
    assert [len(b) for b in batches] == [2, 2, 1]


def test_oversized_source_gets_its_own_batch():
    sources = [_source("big", "x" * 500), _source("small", "x" * 10)]
    batches = _batch_sources(sources, budget=100)
    assert [s.filename for b in batches for s in b] == ["big", "small"]
    assert len(batches) == 2  # the oversized one is not merged with the small one


def test_dedup_drops_same_module_and_title_case_insensitive():
    drafts = [
        _draft("WO", "Auto-close work orders"),
        _draft("WO", "auto-close   work orders"),  # same after normalizing
        _draft("ASSET", "Auto-close work orders"),  # different module -> kept
    ]
    unique = _dedup(drafts)
    assert len(unique) == 2
    assert unique[0].module == "WO"
    assert unique[1].module == "ASSET"
