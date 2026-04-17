"""생성 결과물 파일 서빙 API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(prefix="/results", tags=["results"])

OUTPUT_ROOT = Path("output")


def _resolve_latest(slug: str) -> Path:
    """output/{slug}/latest/ 경로를 반환. 존재하지 않으면 404."""
    latest = OUTPUT_ROOT / slug / "latest"
    if not latest.exists():
        raise HTTPException(status_code=404, detail=f"No results for slug: {slug}")
    return latest


@router.get("/{slug}/latest/html")
def get_html(slug: str) -> HTMLResponse:
    path = _resolve_latest(slug) / "content" / "seo-content.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="HTML not found")
    return HTMLResponse(content=path.read_text(encoding="utf-8"))


@router.get("/{slug}/latest/markdown")
def get_markdown(slug: str) -> FileResponse:
    path = _resolve_latest(slug) / "content" / "seo-content.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Markdown not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8")


@router.get("/{slug}/latest/outline")
def get_outline(slug: str) -> FileResponse:
    path = _resolve_latest(slug) / "content" / "outline.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Outline not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8")


@router.get("/{slug}/latest/images/{filename}")
def get_image(slug: str, filename: str) -> FileResponse:
    # 경로 순회 공격 방지
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = _resolve_latest(slug) / "images" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    suffix = path.suffix.lower()
    media_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    media_type = media_map.get(suffix, "application/octet-stream")
    return FileResponse(path, media_type=media_type)


@router.get("/{slug}/runs")
def list_runs(slug: str) -> list[dict[str, str]]:
    slug_dir = OUTPUT_ROOT / slug
    if not slug_dir.exists():
        raise HTTPException(status_code=404, detail=f"No results for slug: {slug}")
    runs = []
    for child in sorted(slug_dir.iterdir(), reverse=True):
        if child.is_dir() and child.name != "latest":
            runs.append({"timestamp": child.name, "path": str(child)})
    return runs
