"""웹 API 인증. X-API-Key 헤더 기반 단순 인증.

settings.admin_api_key 가 None 이면 인증 비활성 (개발 모드). 운영 배포 시 반드시 설정.
WebSocket 은 브라우저에서 커스텀 헤더를 보낼 수 없으므로 query param `token` 도 허용.

결과물 라우터(`/api/results/*`) 는 iframe/img 에서 헤더를 못 붙이므로 `?token=` 쿼리를
허용하되, 쿼리 토큰은 **슬러그 전용 단명 서명 토큰**만 받는다 (signed_token 모듈).
관리자 API 키 자체를 URL 에 실어 브라우저 history·프록시 로그로 새는 것을 막는다.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Request, WebSocket, status

from config.settings import settings
from web.api.signed_token import verify as verify_signed_token

logger = logging.getLogger(__name__)
_warned = False


def _auth_enabled() -> bool:
    global _warned
    if not settings.admin_api_key:
        if not _warned:
            logger.warning("ADMIN_API_KEY 미설정 — 웹 API 인증 비활성 상태 (개발 모드)")
            _warned = True
        return False
    return True


def _equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def require_api_key(request: Request) -> None:
    """HTTP 엔드포인트 Depends. X-API-Key 헤더 기반 검증.

    헤더 외에 `?token=` 쿼리로 관리자 키가 오는 것은 **허용하지 않는다**. iframe/img
    같은 헤더 미지원 환경은 `require_api_key_or_signed_token` 을 사용해 슬러그 전용
    단명 토큰만 받도록 분리되어 있다.
    """
    if not _auth_enabled():
        return
    provided = request.headers.get("x-api-key") or ""
    expected = settings.admin_api_key or ""
    if not provided or not _equal(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


def require_slug_access(slug: str, request: Request) -> None:
    """결과물 조회용. 헤더 X-API-Key 또는 ?token=<signed slug token> 허용.

    signed token 은 slug 에 바인딩된 HMAC + 5분 TTL 이라 새도 해당 slug, 해당 시점에만
    유효하다. 관리자 키 자체가 URL 에 실리지 않도록 query 경로에선 서명 토큰만 검증한다.
    """
    if not _auth_enabled():
        return

    header_key = request.headers.get("x-api-key") or ""
    expected = settings.admin_api_key or ""
    if header_key and _equal(header_key, expected):
        return

    token = request.query_params.get("token") or ""
    if token and verify_signed_token(token, "slug", slug):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
    )


async def require_api_key_ws(websocket: WebSocket, job_id: str | None = None) -> bool:
    """WebSocket 인증. 실패 시 close() 후 False 반환.

    인정되는 자격:
      - 헤더 `X-API-Key` (일반적으로 브라우저에선 못 씀)
      - `?token=<signed job token>` (권장, 단명 HMAC)
      - `?token=<admin_api_key>` (하위 호환 — 기존 프론트 버전 보호용)

    admin_api_key 를 URL 로 받는 경로는 과도기 호환 목적이며, 프론트가 새 signed token
    API 로 전환되면 제거 예정.
    """
    if not _auth_enabled():
        return True
    header_key = websocket.headers.get("x-api-key") or ""
    expected = settings.admin_api_key or ""
    if header_key and _equal(header_key, expected):
        return True

    token = websocket.query_params.get("token") or ""
    if token:
        if job_id is not None and verify_signed_token(token, "job", job_id):
            return True
        # 하위 호환: 기존 프론트는 admin_api_key 를 ?token= 로 넣음
        if _equal(token, expected):
            return True

    await websocket.close(code=4401, reason="Invalid or missing credentials")
    return False
