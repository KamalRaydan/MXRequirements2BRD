"""PDF text extraction via PyMuPDF."""
import pymupdf


def extract(filepath: str) -> tuple[str, int]:
    """Return (full text, page count)."""
    with pymupdf.open(filepath) as doc:
        pages = [page.get_text() for page in doc]
        return "\n\n".join(pages).strip(), len(pages)
