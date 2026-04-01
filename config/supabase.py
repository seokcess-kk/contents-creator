"""Supabase 연결 설정.

사용법:
    from config.supabase import get_client
    supabase = get_client()
    result = supabase.table("client_profiles").select("*").execute()
"""

from __future__ import annotations

from supabase import Client, create_client

from domain.common.config import settings


def get_client() -> Client:
    """Supabase 클라이언트를 반환한다."""
    return create_client(settings.supabase_url, settings.supabase_key)
