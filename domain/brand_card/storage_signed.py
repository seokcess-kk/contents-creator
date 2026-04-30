"""브랜드 sources 업로드용 Supabase Storage signed URL 헬퍼.

Vercel 함수 페이로드 4.5MB 한계를 우회하기 위해 브라우저가 Supabase Storage 로
직접 PUT 한다. 백엔드는 signed upload URL 발급 + confirm 단계의 다운로드만 담당.

흐름:
1. `create_upload_url(brand_id, sha256, suffix)` → signed PUT URL + token
2. 브라우저: PUT signed_url (Vercel 우회)
3. `download_object(storage_path)` → bytes (confirm 단계 source_parser 입력)

격리 도메인 규칙: 본 모듈은 `config.supabase` (인프라) 만 import. 다른 domain
import 금지. brand_card → compliance 예외와 무관.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from config.settings import settings
from config.supabase import get_client

logger = logging.getLogger(__name__)


class SignedUploadUrl(BaseModel):
    """create_upload_url 반환값.

    `upload_url` 은 브라우저가 PUT 할 절대 URL. `upload_token` 은 일부 SDK 가
    URL 과 별도로 토큰을 반환하는 케이스 대비. `storage_path` 는 confirm
    단계에서 백엔드가 download 할 객체 키.
    """

    upload_url: str
    upload_token: str | None = None
    storage_path: str
    expires_at: datetime


class StorageSignedError(Exception):
    """signed URL 발급 또는 다운로드 실패."""


def build_storage_path(brand_id: str, sha256: str, suffix: str, *, prefix: str = "sources") -> str:
    """저장 경로 단일 출처. confirm 단계 검증도 같은 함수 결과와 비교.

    형식: `{brand_id}/{prefix}/{sha256}{suffix}` — path traversal 방지를 위해
    suffix 는 사전에 화이트리스트 검증된 값만 받는다.

    prefix 기본값 `"sources"` 는 brand_message_sources 호환. 미디어 자산은
    `prefix="media"` 로 호출.
    """
    return f"{brand_id}/{prefix}/{sha256}{suffix}"


def create_upload_url(
    brand_id: str,
    sha256: str,
    suffix: str,
    *,
    bucket: str | None = None,
    prefix: str = "sources",
    ttl_seconds: int | None = None,
) -> SignedUploadUrl:
    """Supabase Storage 에 signed PUT URL 발급. 단명(기본 5분).

    bucket/prefix/ttl_seconds 미지정 시 brand_sources 의 기본값을 사용한다 —
    기존 호출부 (sources) 와의 호환을 위해 키워드 인자로 노출.
    """
    storage_path = build_storage_path(brand_id, sha256, suffix, prefix=prefix)
    target_bucket = bucket or settings.brand_sources_bucket
    ttl = ttl_seconds or settings.brand_sources_signed_url_ttl_seconds

    try:
        client = get_client()
        resp = client.storage.from_(target_bucket).create_signed_upload_url(storage_path)
    except Exception as exc:
        logger.warning(
            "storage_signed.upload_failed bucket=%s path=%s",
            target_bucket,
            storage_path,
            exc_info=True,
        )
        raise StorageSignedError(f"signed upload URL 발급 실패: {exc}") from exc

    upload_url, token = _extract_signed_upload(resp)
    if not upload_url:
        logger.warning(
            "storage_signed.upload_no_url bucket=%s path=%s resp=%s",
            target_bucket,
            storage_path,
            resp,
        )
        raise StorageSignedError("signed upload URL 응답 형식 오류")

    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    logger.info(
        "storage_signed.upload ok bucket=%s path=%s expires=%s",
        target_bucket,
        storage_path,
        expires_at,
    )
    return SignedUploadUrl(
        upload_url=upload_url,
        upload_token=token,
        storage_path=storage_path,
        expires_at=expires_at,
    )


def download_object(storage_path: str, *, bucket: str | None = None) -> bytes:
    """Supabase Storage 에서 객체 바이트 다운로드. confirm 단계용.

    bucket 미지정 시 brand_sources 기본값. 본 함수는 storage_path 패턴을 검증
    하지 않는다 — 호출자(라우터)가 init 단계 발급 패턴과 비교 후 호출.
    """
    target_bucket = bucket or settings.brand_sources_bucket
    try:
        client = get_client()
        data = client.storage.from_(target_bucket).download(storage_path)
    except Exception as exc:
        logger.warning(
            "storage_signed.download_failed bucket=%s path=%s",
            target_bucket,
            storage_path,
            exc_info=True,
        )
        raise StorageSignedError(f"storage 다운로드 실패: {exc}") from exc

    if not isinstance(data, bytes):
        raise StorageSignedError(f"storage 응답이 bytes 가 아님: {type(data).__name__}")
    if not data:
        raise StorageSignedError("storage 객체가 비어있음")
    return data


def create_download_url(
    storage_path: str,
    *,
    bucket: str | None = None,
    ttl_seconds: int = 300,
) -> str:
    """다운로드용 단명 signed URL 발급. `<img src>` redirect 용도.

    bucket 미지정 시 brand_sources 기본값. 실패 시 StorageSignedError.
    """
    target_bucket = bucket or settings.brand_sources_bucket
    try:
        client = get_client()
        resp = client.storage.from_(target_bucket).create_signed_url(
            path=storage_path,
            expires_in=ttl_seconds,
        )
    except Exception as exc:
        logger.warning(
            "storage_signed.download_url_failed bucket=%s path=%s",
            target_bucket,
            storage_path,
            exc_info=True,
        )
        raise StorageSignedError(f"download signed URL 발급 실패: {exc}") from exc

    url = resp.get("signedURL") or resp.get("signed_url") if isinstance(resp, dict) else None
    if not url:
        raise StorageSignedError(f"download signed URL 응답 형식 오류: {resp}")
    return str(url)


def remove_object(storage_path: str, *, bucket: str | None = None) -> bool:
    """confirm 실패 또는 정리 시 객체 삭제. best-effort."""
    target_bucket = bucket or settings.brand_sources_bucket
    try:
        client = get_client()
        client.storage.from_(target_bucket).remove([storage_path])
        return True
    except Exception:
        logger.warning(
            "storage_signed.remove_failed bucket=%s path=%s",
            target_bucket,
            storage_path,
            exc_info=True,
        )
        return False


def _extract_signed_upload(resp: object) -> tuple[str | None, str | None]:
    """SDK 응답에서 (signed_url, token) 추출. supabase-py 응답 키는 버전에 따라
    `signedURL`/`signed_url` 두 형식이 혼재한다.
    """
    if not isinstance(resp, dict):
        return None, None
    url = resp.get("signedURL") or resp.get("signed_url")
    token = resp.get("token")
    return (str(url) if url else None, str(token) if token else None)
