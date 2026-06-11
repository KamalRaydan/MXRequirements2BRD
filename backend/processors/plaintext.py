"""TXT / Markdown extraction — read as UTF-8, tolerate bad bytes."""


def extract(filepath: str) -> str:
    with open(filepath, encoding="utf-8", errors="replace") as f:
        return f.read().strip()
