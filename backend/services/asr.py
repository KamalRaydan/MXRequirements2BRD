"""Local speech-to-text for audio/video sources (spec §18, Milestone 5).

Prefers NVIDIA Parakeet via parakeet-mlx (Apple Silicon — fast and accurate);
falls back to faster-whisper wherever Parakeet isn't installed. The model is
loaded lazily on first use and kept for the life of the process. Audio never
leaves the machine (spec "Security & data").
"""
import os
import threading

import config

PARAKEET_MODEL = "mlx-community/parakeet-tdt-0.6b-v2"
WHISPER_MODEL = "small"

# Model weights download here on first use (not the user's home directory),
# so the packaged desktop app has one predictable, writable cache.
MODELS_DIR = config.APP_DATA_DIR / "models"

_lock = threading.Lock()
_engine: tuple | None = None  # ("parakeet" | "whisper", loaded model)


def ensure_ffmpeg_on_path() -> None:
    """parakeet-mlx runs whatever `ffmpeg` it finds on PATH. The bundled
    imageio-ffmpeg binary has a versioned filename and lives off PATH, so
    expose it through a plain `ffmpeg` symlink in the app-data dir."""
    import shutil

    if shutil.which("ffmpeg"):
        return
    import imageio_ffmpeg

    bin_dir = MODELS_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    link = bin_dir / "ffmpeg"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def _load_engine() -> tuple:
    os.environ.setdefault("HF_HOME", str(MODELS_DIR / "huggingface"))
    try:
        from parakeet_mlx import from_pretrained
        ensure_ffmpeg_on_path()
        return ("parakeet", from_pretrained(PARAKEET_MODEL))
    except ImportError:
        from faster_whisper import WhisperModel
        return ("whisper", WhisperModel(WHISPER_MODEL, download_root=str(MODELS_DIR / "whisper")))


def transcribe(wav_path: str) -> str:
    """Transcribe a 16 kHz mono WAV file to plain text."""
    global _engine
    with _lock:  # one model load, and ASR engines aren't thread-safe
        if _engine is None:
            _engine = _load_engine()
        kind, model = _engine
        if kind == "parakeet":
            # chunk_duration keeps hour-long workshop recordings from loading whole into memory
            return model.transcribe(wav_path, chunk_duration=120.0).text.strip()
        segments, _info = model.transcribe(wav_path)
        return " ".join(segment.text.strip() for segment in segments).strip()
