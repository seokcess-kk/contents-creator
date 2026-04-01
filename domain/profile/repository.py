"""클라이언트 프로필 저장소. Supabase 우선, 실패 시 로컬 JSON 폴백."""

from __future__ import annotations

import logging

from domain.common.config import settings
from domain.common.repository import JsonFileRepository, Repository, SupabaseRepository
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)


def get_profile_repository() -> Repository[ClientProfile]:
    """프로필 저장소 인스턴스를 반환한다."""
    if settings.supabase_url and settings.supabase_key:
        try:
            repo = SupabaseRepository(
                table_name="client_profiles",
                model_class=ClientProfile,
            )
            logger.info("프로필 저장소: Supabase")
            return repo
        except Exception as e:
            logger.warning("Supabase 연결 실패, 로컬 JSON 폴백: %s", e)

    logger.info("프로필 저장소: 로컬 JSON")
    return JsonFileRepository(
        base_dir=settings.data_dir,
        collection="profiles",
        model_class=ClientProfile,
    )
