"""Supabase Storage 헬퍼.

Render 컨테이너는 재배포 시 파일시스템이 초기화되므로 이미지 등 바이너리 산출물은
Supabase Storage 의 `results` 버킷(Private)에 업로드하고, 조회 시 Signed URL 로 서빙한다.

- 업로드: service_role 키 기준. RLS 우회.
- 조회: 짧은 TTL 의 Signed URL 로 리다이렉트. 토큰 유출 영향 최소화.
- 실패 허용: upload 실패는 로그만 남기고 예외 전파하지 않는다 (로컬 파일은 남아 있어 CLI 로 복구 가능).
"""

from __future__ import annotations

import logging

from config.settings import settings
from config.supabase import get_client

logger = logging.getLogger(__name__)

DEFAULT_SIGNED_URL_TTL = 300  # 5분


def upload_bytes(key: str, data: bytes, content_type: str) -> bool:
    """Supabase Storage 에 바이트 업로드.

    Args:
        key: 버킷 내 경로 (예: `slug/20260101-1200/images/image_1.jpg`)
        data: 파일 바이트
        content_type: MIME (예: `image/jpeg`)

    Returns:
        성공 True, 실패 False (로그 기록).

    같은 key 로 재업로드 시 upsert=True 로 덮어쓴다 (재생성 플래그 대응).
    """
    try:
        client = get_client()
        client.storage.from_(settings.storage_bucket).upload(
            path=key,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        logger.info("storage.upload ok key=%s size=%d", key, len(data))
        return True
    except Exception:
        logger.warning("storage.upload failed key=%s", key, exc_info=True)
        return False


def get_signed_url(key: str, ttl_seconds: int = DEFAULT_SIGNED_URL_TTL) -> str | None:
    """Signed URL 반환. 실패 시 None.

    TTL 은 짧게 (기본 5분) — 리다이렉트 직후 브라우저가 로드하므로 충분.
    """
    try:
        client = get_client()
        resp = client.storage.from_(settings.storage_bucket).create_signed_url(
            path=key,
            expires_in=ttl_seconds,
        )
        url: str | None = resp.get("signedURL") if isinstance(resp, dict) else None
        if not url:
            logger.warning("storage.signed_url no_url key=%s resp=%s", key, resp)
            return None
        return url
    except Exception:
        logger.warning("storage.signed_url failed key=%s", key, exc_info=True)
        return None
