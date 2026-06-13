"""GET source text endpoint — what a source contributes to the BRD (Milestone 5)."""
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def project(client, tmp_path):
    return client.post("/projects", json={
        "client_name": "Text Co", "project_name": "Source Text Test",
        "project_date": "2026-06-13", "maximo_version": "mas-9",
        "folder_path": str(tmp_path / "text"),
    }).json()


def _upload_txt(client, project_id, name, body):
    return client.post(
        f"/projects/{project_id}/sources/upload",
        files={"file": (name, body)},
    ).json()


def test_returns_extracted_text_for_ready_source(client, project):
    source = _upload_txt(client, project["id"], "notes.txt", b"Operators need offline work orders.")

    response = client.get(f"/projects/{project['id']}/sources/{source['id']}/text")

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Operators need offline work orders."
    assert body["char_count"] == len("Operators need offline work orders.")


def test_404_for_unknown_source(client, project):
    response = client.get(f"/projects/{project['id']}/sources/does-not-exist/text")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_409_when_not_yet_extracted(client, project, monkeypatch):
    # Upload without the background extraction running, so the source stays unextracted
    import routes.sources as sources_routes
    monkeypatch.setattr(sources_routes.BackgroundTasks, "add_task", lambda *a, **k: None)

    source = _upload_txt(client, project["id"], "pending.txt", b"not processed yet")

    response = client.get(f"/projects/{project['id']}/sources/{source['id']}/text")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_EXTRACTED"
