"""Full pipeline with a mocked LLM: create project -> upload TXT -> wait EXTRACTED
-> generate -> run DONE -> DOCX downloads (spec §17.2)."""
import pytest
from fastapi.testclient import TestClient

import agents.runner
import main
from models.pipeline import (AnalysisDraft, NarrativeSection, NarrativeSet,
                             RequirementDraft)
from services import keystore


class FakeLLM:
    """Stands in for LLMClient — returns canned, schema-valid responses."""

    def __init__(self, api_key, model_id, provider="anthropic"):
        pass

    def complete(self, messages, max_tokens=4096, system=None):
        return "summary text"

    def complete_json(self, messages, schema, max_tokens=8192, system=None):
        if schema is AnalysisDraft:
            return AnalysisDraft(
                requirements=[RequirementDraft(
                    module="WO", title="Auto-close work orders",
                    description="Work orders must auto-close after 30 days",
                    requirement_type="functional", priority="high",
                    source_ref="notes.txt", source_timestamp="2026-05-15T09:00:00Z",
                    sort_order=1,
                )],
                modules_referenced=["WO"],
            )
        return NarrativeSet(narratives=[
            NarrativeSection(section_id="executive_summary",
                             title="Executive Summary", body="The summary."),
        ])


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(agents.runner, "LLMClient", FakeLLM)
    monkeypatch.setattr(keystore, "get_api_key", lambda provider: "test-key")
    with TestClient(main.app) as test_client:
        yield test_client


def test_full_pipeline_with_mock_llm(client, tmp_path):
    project = client.post("/projects", json={
        "client_name": "Test Co", "project_name": "Pipeline Test",
        "project_date": "2026-06-11", "maximo_version": "mas-9",
        "folder_path": str(tmp_path / "proj"),
    }).json()

    # Upload — TestClient runs the background extraction before returning control
    upload = client.post(
        f"/projects/{project['id']}/sources/upload",
        files={"file": ("notes.txt", b"WOs must auto-close after 30 days.", "text/plain")},
    )
    assert upload.status_code == 201

    sources = client.get(f"/projects/{project['id']}/sources").json()
    assert sources[0]["processing_status"] == "EXTRACTED"

    # Generate — pipeline background task also completes before control returns
    generate = client.post(f"/projects/{project['id']}/generate")
    assert generate.status_code == 202
    run_id = generate.json()["run_id"]

    run = client.get(f"/pipeline/{run_id}").json()
    assert run["status"] == "DONE", run.get("error_message")
    assert run["sources_used_count"] == 1

    download = client.get(f"/pipeline/{run_id}/download")
    assert download.status_code == 200
    assert download.content[:2] == b"PK"  # docx files are zip archives


def test_generate_blocked_without_sources(client, tmp_path):
    project = client.post("/projects", json={
        "client_name": "Empty Co", "project_name": "No Sources",
        "project_date": "2026-06-11", "maximo_version": "mas-9",
        "folder_path": str(tmp_path / "empty"),
    }).json()

    response = client.post(f"/projects/{project['id']}/generate")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_SOURCES"
