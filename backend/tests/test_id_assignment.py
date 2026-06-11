"""BRD-{MODULE}-{NNN} assignment is deterministic (spec §7.5)."""
from agents.analyzer import assign_ids
from models.pipeline import RequirementDraft


def _draft(module: str, title: str, sort_order: int) -> RequirementDraft:
    return RequirementDraft(
        module=module,
        title=title,
        description=f"Description of {title}",
        requirement_type="functional",
        priority="high",
        source_ref="workshop.pdf",
        source_timestamp="2026-05-15T09:00:00Z",
        sort_order=sort_order,
    )


def test_ids_sequence_per_module():
    drafts = [
        _draft("WO", "Second WO req", 2),
        _draft("ASSET", "Asset req", 1),
        _draft("WO", "First WO req", 1),
    ]
    result = assign_ids(drafts)
    ids = {r.title: r.id for r in result}

    assert ids["First WO req"] == "BRD-WO-001"
    assert ids["Second WO req"] == "BRD-WO-002"
    assert ids["Asset req"] == "BRD-ASSET-001"


def test_unknown_module_falls_back_to_general():
    result = assign_ids([_draft("NOTAMODULE", "Odd req", 1)])
    assert result[0].id == "BRD-GENERAL-001"
    assert result[0].module == "GENERAL"


def test_zero_padding_three_digits():
    drafts = [_draft("PM", f"Req {i}", i) for i in range(1, 12)]
    result = assign_ids(drafts)
    assert result[0].id == "BRD-PM-001"
    assert result[10].id == "BRD-PM-011"
