"""Media extractors (Milestone 5): audio/video transcription and image vision.

The bundled ffmpeg runs for real on tiny generated WAV fixtures; the ASR model
and the vision API are mocked — tests download nothing and touch no network.
"""
import math
import struct
import wave

import pytest
from fastapi.testclient import TestClient

import main
import processors
from db.database import Base, SessionLocal, engine
from services import asr, keystore
from services.llm_client import LLMClient, LLMError


def make_wav(path, seconds=0.3):
    """A tiny mono 16 kHz WAV with a 440 Hz tone (stdlib only)."""
    frames = int(16000 * seconds)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(
            struct.pack("<h", int(20000 * math.sin(2 * math.pi * 440 * i / 16000)))
            for i in range(frames)
        ))


@pytest.fixture
def fake_asr(monkeypatch):
    """Replace the ASR engine; capture the WAV path it was handed."""
    seen = {}

    def fake_transcribe(wav_path):
        seen["wav_path"] = wav_path
        return "The work order backlog must be reviewed weekly."

    monkeypatch.setattr(asr, "transcribe", fake_transcribe)
    return seen


# ---- audio ----

def test_audio_extract_converts_and_transcribes(tmp_path, fake_asr):
    f = tmp_path / "interview.wav"
    make_wav(f)
    text, pages = processors.extract_text("audio", str(f))
    assert "backlog" in text
    assert pages is None
    # the engine gets the normalised temp WAV, not the original upload
    assert fake_asr["wav_path"].endswith(".wav") and fake_asr["wav_path"] != str(f)


def test_audio_corrupt_file_raises(tmp_path, fake_asr):
    f = tmp_path / "broken.mp3"
    f.write_bytes(b"this is not audio")
    with pytest.raises(ValueError, match="No readable audio"):
        processors.extract_text("audio", str(f))


def test_audio_empty_transcript_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(asr, "transcribe", lambda wav: "")
    f = tmp_path / "silence.wav"
    make_wav(f)
    with pytest.raises(ValueError, match="no recognisable speech"):
        processors.extract_text("audio", str(f))


def test_ensure_ffmpeg_on_path_links_bundled_binary(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)  # pretend no system ffmpeg
    asr.ensure_ffmpeg_on_path()
    link = asr.MODELS_DIR / "bin" / "ffmpeg"
    assert link.is_symlink() and link.resolve().exists()


# ---- video (audio track only in M5) ----

def test_video_uses_audio_track(tmp_path, fake_asr):
    # ffmpeg sniffs content, not extensions — a WAV named .mov exercises the
    # same "pull the audio stream out of a container" path
    f = tmp_path / "workshop.mov"
    make_wav(f)
    text, _ = processors.extract_text("video", str(f))
    assert "reviewed weekly" in text


# ---- image (provider vision) ----

def test_image_without_api_key_says_settings(tmp_path, monkeypatch):
    Base.metadata.create_all(engine)
    monkeypatch.setattr(keystore, "get_api_key", lambda provider: None)
    f = tmp_path / "whiteboard.png"
    f.write_bytes(b"\x89PNG fake")
    with pytest.raises(ValueError, match="Settings"):
        processors.extract_text("image", str(f))


def test_image_extracts_via_vision(tmp_path, monkeypatch):
    Base.metadata.create_all(engine)
    monkeypatch.setattr(keystore, "get_api_key", lambda provider: "test-key")
    monkeypatch.setattr(LLMClient, "describe_image",
                        lambda self, filepath: "Whiteboard: SLA escalation after 4 hours")
    f = tmp_path / "whiteboard.png"
    f.write_bytes(b"\x89PNG fake")
    text, _ = processors.extract_text("image", str(f))
    assert "SLA escalation" in text


def test_describe_image_rejects_unknown_format(tmp_path):
    client = LLMClient(api_key="k", model_id="claude-sonnet-4-6", provider="anthropic")
    f = tmp_path / "scan.tiff"
    f.write_bytes(b"fake")
    with pytest.raises(LLMError, match="Unsupported image format"):
        client.describe_image(str(f))


def test_describe_image_sends_base64_to_anthropic(tmp_path, monkeypatch):
    client = LLMClient(api_key="k", model_id="claude-sonnet-4-6", provider="anthropic")
    captured = {}

    class FakeBlock:
        type = "text"
        text = "OCR result"

    class FakeResponse:
        content = [FakeBlock()]

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(client._anthropic.messages, "create", fake_create)
    f = tmp_path / "slide.png"
    f.write_bytes(b"\x89PNG fake image bytes")

    assert client.describe_image(str(f)) == "OCR result"
    image_block = captured["messages"][0]["content"][0]
    assert image_block["type"] == "image"
    assert image_block["source"]["media_type"] == "image/png"
    assert image_block["source"]["data"]  # base64 payload present


# ---- upload + retry flow through the API ----

@pytest.fixture
def client(monkeypatch, fake_asr):
    with TestClient(main.app) as test_client:
        yield test_client


def _make_project(client, tmp_path):
    return client.post("/projects", json={
        "client_name": "Test Co", "project_name": "Media Test",
        "project_date": "2026-06-12", "maximo_version": "mas-8",
        "folder_path": str(tmp_path / "proj"),
    }).json()


def test_uploaded_audio_reaches_extracted(client, tmp_path):
    project = _make_project(client, tmp_path)
    wav = tmp_path / "interview.mp3"
    make_wav(wav)

    # TestClient runs the background transcription before returning control
    upload = client.post(
        f"/projects/{project['id']}/sources/upload",
        files={"file": ("interview.mp3", wav.read_bytes(), "audio/mpeg")},
    )
    assert upload.status_code == 201
    assert upload.json()["processing_status"] == "TRANSCRIBING"

    source = client.get(f"/projects/{project['id']}/sources").json()[0]
    assert source["processing_status"] == "EXTRACTED"
    assert source["char_count"] > 0


def test_pre_m5_pending_source_can_be_processed(client, tmp_path):
    project = _make_project(client, tmp_path)
    wav = tmp_path / "old-recording.wav"
    make_wav(wav)

    # Simulate a media file uploaded before Milestone 5: row parked at PENDING
    from db.models import Source
    db = SessionLocal()
    source = Source(
        project_id=project["id"], filename="old-recording.wav", filepath=str(wav),
        filetype="audio", file_size_bytes=wav.stat().st_size,
        source_timestamp=__import__("datetime").datetime.now(),
        processing_status="PENDING",
    )
    db.add(source)
    db.commit()
    source_id = source.id
    db.close()

    retry = client.post(f"/projects/{project['id']}/sources/{source_id}/process")
    assert retry.status_code == 200

    statuses = {s["id"]: s["processing_status"]
                for s in client.get(f"/projects/{project['id']}/sources").json()}
    assert statuses[source_id] == "EXTRACTED"


def test_process_rejects_already_extracted(client, tmp_path):
    project = _make_project(client, tmp_path)
    upload = client.post(
        f"/projects/{project['id']}/sources/upload",
        files={"file": ("notes.txt", b"WOs must auto-close.", "text/plain")},
    ).json()
    response = client.post(f"/projects/{project['id']}/sources/{upload['id']}/process")
    assert response.status_code == 409
