"""웹 API 인증. X-API-Key 헤더 기반 단순 인증.

settings.admin_api_key 가 None 이면 인증 비활성 (개발 모드). 운영 배포 시 반드시 설정.
WebSocket 은 브라우저에서 커스텀 헤더를 보낼 수 없으므로 query param `token` 도 허용.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Request, WebSocket, status

from config.settings import settings

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
    """HTTP 엔드포인트 Depends. X-API-Key 헤더 검증."""
    if not _auth_enabled():
        return
    provided = request.headers.get("x-api-key", "")
    expected = settings.admin_api_key or ""
    if not provided or not _equal(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


async def require_api_key_ws(websocket: WebSocket) -> bool:
    """WebSocket 인증. 실패 시 close() 후 False 반환.

    헤더 또는 query `?token=...` 지원.
    """
    if not _auth_enabled():
        return True
    provided = websocket.headers.get("x-api-key") or websocket.query_params.get("token") or ""
    expected = settings.admin_api_key or ""
    if not provided or not _equal(provided, expected):
        await websocket.close(code=4401, reason="Invalid or missing API key")
        return False
    return True
