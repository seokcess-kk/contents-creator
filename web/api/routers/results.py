"""생성 결과물 파일 서빙 API.

로컬 파일시스템이 1차 소스, Supabase 가 영속 백업.
Render 컨테이너는 재배포/슬립 시 파일이 휘발되므로 없으면 Supabase 에서 조회한다.

- HTML/Markdown/Outline: `generated_contents` 테이블 (slug 기준 최신 행) 에서 조회
- 이미지: `results` Storage 버킷에서 Signed URL 로 리다이렉트
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse

from config.supabase import get_client
from domain.storage import get_signed_url
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"], dependencies=[Depends(require_api_key)])

OUTPUT_ROOT = Path("output")


def _local_latest(slug: str) -> Path | None:
    """output/{slug}/latest/ 가 존재하면 반환, 아니면 None."""
    latest = OUTPUT_ROOT / slug / "latest"
    return latest if latest.exists() else None


_IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")(?:\.\./)?images/([^"?#]+)(")', re.IGNORECASE)


def _rewrite_image_src(html: str, slug: str, request: Request) -> str:
    """브라우저 미리보기용 img src 재작성.

    저장 HTML 의 상대 경로 `(../)?images/xxx` 를 인증된 라우터 절대 경로
    `/api/results/{slug}/latest/images/xxx?token=...` 로 바꾼다.
    네이버 복붙 시에는 클라이언트가 다시 저장본을 받을 것이므로 저장 파일은 변경하지 않는다.
    """
    token = request.query_params.get("token") or request.headers.get("x-api-key") or ""
    qs = f"?token={quote(token)}" if token else ""
    base = f"/api/results/{quote(slug, safe='')}/latest/images"
    return _IMG_SRC_RE.sub(lambda m: f"{m.group(1)}{base}/{m.group(2)}{qs}{m.group(3)}", html)


def _fetch_latest_row(slug: str, columns: str) -> dict | None:
    """generated_contents 에서 slug 최신 행을 조회. 실패/미존재 시 None."""
    try:
        client = get_client()
        resp = (
            client.table("generated_contents")
            .select(columns)
            .eq("slug", slug)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None  # type: ignore[no-any-return]
    except Exception:
        logger.warning("generated_contents.fetch_failed slug=%s", slug, exc_info=True)
        return None


@router.get("/{slug}/latest/html", response_model=None)
def get_html(slug: str, request: Request) -> HTMLResponse:
    latest = _local_latest(slug)
    if latest is not None:
        path = latest / "content" / "seo-content.html"
        if path.exists():
            html = path.read_text(encoding="utf-8")
            return HTMLResponse(content=_rewrite_image_src(html, slug, request))

    row = _fetch_latest_row(slug, "content_html")
    if row and row.get("content_html"):
        return HTMLResponse(content=_rewrite_image_src(row["content_html"], slug, request))
    raise HTTPException(status_code=404, detail="HTML not found")


@router.get("/{slug}/latest/markdown", response_model=None)
def get_markdown(slug: str) -> FileResponse | PlainTextResponse:
    latest = _local_latest(slug)
    if latest is not None:
        path = latest / "content" / "seo-content.md"
        if path.exists():
            return FileResponse(path, media_type="text/markdown; charset=utf-8")

    row = _fetch_latest_row(slug, "content_md")
    if row and row.get("content_md"):
        return PlainTextResponse(row["content_md"], media_type="text/markdown; charset=utf-8")
    raise HTTPException(status_code=404, detail="Markdown not found")


@router.get("/{slug}/latest/outline", response_model=None)
def get_outline(slug: str) -> FileResponse | PlainTextResponse:
    latest = _local_latest(slug)
    if latest is not None:
        path = latest / "content" / "outline.md"
        if path.exists():
            return FileResponse(path, media_type="text/markdown; charset=utf-8")

    row = _fetch_latest_row(slug, "outline_md")
    if row and row.get("outline_md"):
        return PlainTextResponse(row["outline_md"], media_type="text/markdown; charset=utf-8")
    raise HTTPException(status_code=404, detail="Outline not found")


@router.get("/{slug}/latest/images/{filename}", response_model=None)
def get_image(slug: str, filename: str) -> FileResponse | RedirectResponse:
    # 경로 순회 공격 방지
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    latest = _local_latest(slug)
    if latest is not None:
        path = latest / "images" / filename
        if path.exists():
            suffix = path.suffix.lower()
            media_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            media_type = media_map.get(suffix, "application/octet-stream")
            return FileResponse(path, media_type=media_type)

    # Storage fallback — output_path 에서 timestamp 를 얻어 Signed URL 리다이렉트.
    row = _fetch_latest_row(slug, "output_path")
    if not row or not row.get("output_path"):
        raise HTTPException(status_code=404, detail="Image not found")
    output_path = row["output_path"].replace("\\", "/")
    ts = Path(output_path).name  # output/{slug}/{ts}
    key = f"{slug}/{ts}/images/{filename}"
    url = get_signed_url(key)
    if not url:
        raise HTTPException(status_code=404, detail="Image not found")
    return RedirectResponse(url=url, status_code=307)


@router.get("/recent")
def list_recent(limit: int = 50) -> list[dict]:
    """완료된 원고 목록(최신순). generated_contents 테이블 기반 — 영구 저장.

    - limit: 최대 1~200 (기본 50)
    - slug 가 NULL 인 레거시 행은 제외
    """
    limit = max(1, min(limit, 200))
    try:
        client = get_client()
        resp = (
            client.table("generated_contents")
            .select("slug, created_at, compliance_passed, compliance_iterations, output_path")
            .not_.is_("slug", "null")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []  # type: ignore[no-any-return]
    except Exception:
        logger.warning("recent results fetch failed", exc_info=True)
        raise HTTPException(status_code=500, detail="failed to fetch recent results") from None


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
