"""Video → audio track → text (spec §18, Milestone 5).

Only the audio is used: ffmpeg strips the picture and the audio path takes
over. Visual content (e.g., slides in a screen recording) is not analysed in
Milestone 5 — keyframe sampling into the image/vision path is the documented
later extension.
"""
from processors import audio


def extract(filepath: str) -> str:
    return audio.extract(filepath)
