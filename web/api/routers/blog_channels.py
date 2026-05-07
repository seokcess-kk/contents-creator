"""Blog Channels API — 운영자가 보유한 네이버 블로그 채널 CRUD.

발행 시 PublicationForm + CSV 업로드 + 검수 큐가 채널 목록을 참조한다.
발행 자체는 외부 수동 — 본 API 는 단순 메타 + 추적용.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from config.settings import settings
from domain.blog_channel import storage as channel_storage
from domain.blog_channel.model import BlogChannel, BlogChannelDuplicateError
from web.api.auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/blog-channels",
    tags=["blog-channels"],
    dependencies=[Depends(require_api_key)],
)


def _supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


def _supabase_error(exc: Exception, op: str) -> HTTPException:
    msg = str(exc)
    is_missing = "relation" in msg.lower() and "does not exist" in msg.lower()
    detail = (
        "Supabase 의 blog_channels 테이블이 없습니다. config/schema.sql 의 마이그레이션을 적용하세요."
        if is_missing
        else f"Supabase 호출 실패 ({op}): {type(exc).__name__}: {msg}"
    )
    logger.error("blog_channels.%s.failed exc=%s", op, msg, exc_info=True)
    return HTTPException(status_code=503, detail=detail)


# ── 요청 모델 ────────────────────────────────────────────────


class CreateBlogChannelRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    blog_id: str = Field(min_length=1, max_length=100)
    homepage_url: str
    memo: str | None = None
    is_default: bool = False


class UpdateBlogChannelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    blog_id: str | None = Field(default=None, min_length=1, max_length=100)
    homepage_url: str | None = None
    memo: str | None = None
    is_default: bool | None = None


# ── 라우트 ──────────────────────────────────────────────────


@router.get("")
def list_blog_channels() -> dict[str, object]:
    if not _supabase_configured():
        return {"count": 0, "items": [], "warning": "Supabase 미설정"}
    try:
        channels = channel_storage.list_channels(limit=200)
    except Exception as exc:
        raise _supabase_error(exc, "list") from exc
    return {"count": len(channels), "items": [c.model_dump() for c in channels]}


@router.post("", status_code=201)
def create_blog_channel(req: CreateBlogChannelRequest) -> dict[str, object]:
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    channel = BlogChannel(
        name=req.name,
        blog_id=req.blog_id,
        homepage_url=req.homepage_url,
        memo=req.memo,
        is_default=req.is_default,
    )
    try:
        created = channel_storage.create_channel(channel)
    except BlogChannelDuplicateError as exc:
        raise HTTPException(status_code=409, detail=f"중복: {exc}") from exc
    except Exception as exc:
        raise _supabase_error(exc, "create") from exc
    return created.model_dump()


@router.get("/{channel_id}")
def get_blog_channel(channel_id: str) -> dict[str, object]:
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        channel = channel_storage.get_channel(channel_id)
    except Exception as exc:
        raise _supabase_error(exc, "get") from exc
    if channel is None:
        raise HTTPException(status_code=404, detail="채널 미존재")
    return channel.model_dump()


@router.patch("/{channel_id}")
def update_blog_channel(channel_id: str, req: UpdateBlogChannelRequest) -> dict[str, object]:
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        updated = channel_storage.update_channel(
            channel_id,
            name=req.name,
            blog_id=req.blog_id,
            homepage_url=req.homepage_url,
            memo=req.memo,
            is_default=req.is_default,
        )
    except BlogChannelDuplicateError as exc:
        raise HTTPException(status_code=409, detail=f"중복: {exc}") from exc
    except Exception as exc:
        raise _supabase_error(exc, "update") from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="채널 미존재")
    return updated.model_dump()


@router.delete("/{channel_id}")
def delete_blog_channel(channel_id: str) -> Response:
    """채널 삭제. 성공 시 204 No Content. publications/keyword_batch_items 의 FK 는
    ON DELETE SET NULL — 기존 발행 이력은 보존."""
    if not _supabase_configured():
        raise HTTPException(status_code=503, detail="Supabase 미설정")
    try:
        deleted = channel_storage.delete_channel(channel_id)
    except Exception as exc:
        raise _supabase_error(exc, "delete") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="채널 미존재")
    return Response(status_code=204)
