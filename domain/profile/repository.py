"""클라이언트 프로필 저장소."""

from __future__ import annotations

from domain.common.config import settings
from domain.common.repository import JsonFileRepository
from domain.profile.model import ClientProfile


def get_profile_repository() -> JsonFileRepository[ClientProfile]:
    """프로필 저장소 인스턴스를 반환한다."""
    return JsonFileRepository(
        base_dir=settings.data_dir,
        collection="profiles",
        model_class=ClientProfile,
    )
