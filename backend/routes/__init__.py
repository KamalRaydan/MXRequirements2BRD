"""Shared route helpers."""
from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """All API errors use the {error: {code, message}} envelope (spec §10)."""
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
