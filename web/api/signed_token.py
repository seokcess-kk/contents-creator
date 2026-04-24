"""단명 서명 토큰 (HMAC-SHA256) — iframe/img/WS URL 노출 축소.

정적 API 키를 `?token=` 쿼리에 싣는 기존 패턴은 브라우저 history·프록시 로그·
Referer 헤더로 키가 새 나간다. 이 모듈은 (scope, resource_id, 만료) 만 담은 단명
토큰을 발급해, 토큰이 새어도 (a) 해당 scope+id 의 리소스만 접근 가능하고 (b) TTL
만료 후엔 무효가 되도록 한다. API 키 자체는 헤더(`X-API-Key`) 에만 실려야 한다.

scope 값:
  - `slug` : `/api/results/{slug}/*` (HTML/이미지)
  - `job`  : `/api/ws/jobs/{job_id}` (WebSocket)

토큰 포맷: `{scope}.{id_b64}.{exp}.{sig}`
  - scope      : 하드코딩된 ASCII 문자열 ("slug" | "job")
  - id_b64     : 리소스 식별자 (base64url)
  - exp        : unix epoch seconds (발급 시각 + TTL)
  - sig        : HMAC-SHA256(secret, f"{scope}|{id_b64}|{exp}") base64url (no pad)

secret 은 `settings.admin_api_key`. admin_api_key 미설정 시 (dev 모드) 토큰 발급은
401 로 막히고, 검증은 상위 auth 가 이미 비활성이므로 이 모듈 호출 자체가 일어나지
않는다.
"""

from __future__ import annotations

import base64
import hmac
import time
from hashlib import sha256

from config.settings import settings

# 기본 TTL — 5 분. iframe/img 렌더에 충분하고 노출 시 피해를 좁힌다.
DEFAULT_TTL_SECONDS = 300
# 상한 — 사용자가 무한 TTL 로 토큰을 요청해도 이 값으로 clamp. 긴 job (최대 1h) 지원.
MAX_TTL_SECONDS = 7200

_ALLOWED_SCOPES = frozenset({"slug", "job"})


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _secret() -> bytes:
    key = settings.admin_api_key or ""
    return key.encode("utf-8")


def _sign(scope: str, id_b64: str, exp: int) -> str:
    payload = f"{scope}|{id_b64}|{exp}".encode()
    return _b64url_encode(hmac.new(_secret(), payload, sha256).digest())


def mint(scope: str, resource_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> tuple[str, int]:
    """scope+resource_id 전용 단명 토큰 발급. (token, expires_at_epoch) 반환."""
    if scope not in _ALLOWED_SCOPES:
        raise ValueError(f"unknown scope: {scope}")
    ttl = max(30, min(int(ttl_seconds), MAX_TTL_SECONDS))
    exp = int(time.time()) + ttl
    id_b64 = _b64url_encode(resource_id.encode("utf-8"))
    sig = _sign(scope, id_b64, exp)
    return f"{scope}.{id_b64}.{exp}.{sig}", exp


def verify(token: str, scope: str, resource_id: str) -> bool:
    """토큰이 (1) scope 일치 (2) resource_id 일치 (3) 미만료 (4) 서명 일치인지 검증.

    실패 이유는 구분하지 않는다 (oracle 방지).
    """
    if scope not in _ALLOWED_SCOPES:
        return False
    try:
        tok_scope, id_b64, exp_str, sig = token.split(".", 3)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False

    if tok_scope != scope:
        return False
    if exp < int(time.time()):
        return False

    try:
        decoded_id = _b64url_decode(id_b64).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    if decoded_id != resource_id:
        return False

    expected = _sign(scope, id_b64, exp)
    return hmac.compare_digest(expected, sig)
