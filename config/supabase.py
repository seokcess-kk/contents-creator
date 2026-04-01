"""Supabase 연결 설정.

사용법:
    from config.supabase import get_client
    supabase = get_client()
    result = supabase.table("client_profiles").select("*").execute()
"""

import os

from supabase import Client, create_client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)
