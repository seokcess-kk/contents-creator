"""Naver 세션 관리 — requests.Session + .pkl 쿠키 영속.

Adapted from seokcess-kk/auto-publishing@c64b5e7 (MIT) common/session.py.
원본의 멀티 플랫폼 분기를 제거하고 네이버 전용으로 좁혔다.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# 프로젝트 루트의 .sessions/ — 채널별 .pkl 1개씩 영속
_SESSION_DIR = Path(__file__).resolve().parents[2] / ".sessions"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_NAVER_DOMAINS = (".naver.com", "blog.naver.com", "cafe.naver.com")


class SessionManager:
    """네이버 채널별 requests.Session + .pkl 쿠키 영속 래퍼.

    name 은 보통 `naver_blog_{blog_id}` 또는 채널 UUID. .sessions/<name>.pkl 에
    쿠키 dict 저장. load() 가 False 반환 시 로그인 단계 (CDP → RSA) 진입.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.cookie_path = _SESSION_DIR / f"{name}.pkl"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})
        _SESSION_DIR.mkdir(parents=True, exist_ok=True)

    # ── 영속 ────────────────────────────────────────

    def load(self) -> bool:
        """저장된 쿠키 로드. 파일 없거나 빈 dict 면 False."""
        if not self.cookie_path.exists():
            logger.debug("session.no_cache name=%s", self.name)
            return False
        try:
            with self.cookie_path.open("rb") as f:
                cookies = pickle.load(f)  # noqa: S301 — 자가 생성 파일만 로드
        except Exception as exc:
            logger.warning("session.load_failed name=%s err=%s", self.name, exc)
            return False

        if not cookies:
            return False

        if isinstance(cookies, dict):
            for cname, cvalue in cookies.items():
                for domain in _NAVER_DOMAINS:
                    self.session.cookies.set(cname, cvalue, domain=domain)
        else:
            self.session.cookies.update(cookies)
        logger.info("session.loaded name=%s n_cookies=%d", self.name, len(self.session.cookies))
        return True

    def save(self) -> None:
        """현재 쿠키를 .pkl 로 영속. 동일 name 호출은 덮어씀."""
        cookies = {c.name: c.value for c in self.session.cookies}
        with self.cookie_path.open("wb") as f:
            pickle.dump(cookies, f)
        logger.info("session.saved name=%s n_cookies=%d", self.name, len(cookies))

    def delete(self) -> None:
        """쿠키 파일 삭제. 재로그인 강제 시 사용."""
        if self.cookie_path.exists():
            self.cookie_path.unlink()
            logger.info("session.deleted name=%s", self.name)

    def has_login_cookie(self) -> bool:
        """NID_AUT 또는 NID_SES 존재 여부. RabbitWrite 전 사전 검증용."""
        names = {c.name for c in self.session.cookies}
        return "NID_AUT" in names or "NID_SES" in names

    # ── 호출 위임 ────────────────────────────────────

    def get(self, url: str, **kwargs: object) -> requests.Response:
        return self.session.get(url, **kwargs)  # type: ignore[arg-type]

    def post(self, url: str, **kwargs: object) -> requests.Response:
        return self.session.post(url, **kwargs)  # type: ignore[arg-type]


__all__ = ["SessionManager"]
