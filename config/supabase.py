"""Supabase 클라이언트 싱글톤.

모든 DB 접근은 `get_client()` 를 거친다. 개별 repository 파일에서
`create_client()` 직접 호출 금지.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.settings import require

if TYPE_CHECKING:
    from supabase import Client

_client: Client | None = None


def get_client() -> Client:
    """Supabase 클라이언트를 가져온다. 최초 호출 시 생성.

    Raises:
        RuntimeError: supabase_url 또는 supabase_key 가 config/.env 에 없을 때
    """
    global _client
    if _client is None:
        from supabase import create_client

        _client = create_client(
            require("supabase_url"),
            require("supabase_key"),
        )
    return _client


def reset_client() -> None:
    """테스트용 — 싱글톤 초기화."""
    global _client
    _client = None
