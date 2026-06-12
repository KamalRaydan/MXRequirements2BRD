"""Audio → text via local speech-to-text (spec §8, Milestone 5).

Any supported input (mp3/wav/m4a/ogg — or a video container, since -vn drops
the picture) is first normalised to 16 kHz mono WAV with the bundled ffmpeg,
so the ASR engine always sees one known format.
"""
import subprocess
import tempfile
from pathlib import Path

from services import asr


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg  # ships a static ffmpeg binary — no system install

    return imageio_ffmpeg.get_ffmpeg_exe()


def to_wav(filepath: str) -> str:
    """Convert any audio (or video) file to a temp 16 kHz mono WAV. Caller deletes it."""
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    out.close()
    result = subprocess.run(
        [_ffmpeg_exe(), "-y", "-i", filepath, "-vn", "-ac", "1", "-ar", "16000", out.name],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        Path(out.name).unlink(missing_ok=True)
        raise ValueError("No readable audio in this file — it may be corrupt or have no audio track")
    return out.name


def extract(filepath: str) -> str:
    wav = to_wav(filepath)
    try:
        text = asr.transcribe(wav)
    finally:
        Path(wav).unlink(missing_ok=True)
    if not text:
        raise ValueError("The audio contained no recognisable speech")
    return text
