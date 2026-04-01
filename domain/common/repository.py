"""저장소 추상화. Supabase 기본, JsonFileRepository는 폴백."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class Repository(Generic[T]):
    """저장소 인터페이스."""

    def save(self, item: T) -> str:
        raise NotImplementedError

    def get(self, item_id: str) -> T | None:
        raise NotImplementedError

    def list_all(self) -> list[T]:
        raise NotImplementedError

    def delete(self, item_id: str) -> bool:
        raise NotImplementedError


class SupabaseRepository(Repository[T]):
    """Supabase 기반 저장소.

    Pydantic 모델을 Supabase 테이블에 CRUD한다.
    id 필드가 없으면 서버측에서 UUID를 생성한다.
    """

    def __init__(self, table_name: str, model_class: type[T]) -> None:
        from domain.common.config import settings

        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY가 설정되지 않았습니다.")

        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_key)
        self._table = table_name
        self._model_class = model_class

    def save(self, item: T) -> str:
        data = item.model_dump(mode="json")

        # id가 비어있으면 제거하여 서버측 gen_random_uuid() 사용
        item_id = data.get("id", "")
        if not item_id:
            data.pop("id", None)

        # Pydantic 전용 필드 중 DB에 없는 컬럼 제거
        data.pop("confidence_scores", None)

        result = self._client.table(self._table).upsert(data).execute()

        if result.data:
            saved_id = result.data[0].get("id", item_id)
            logger.info("Supabase 저장: %s/%s", self._table, saved_id)
            return str(saved_id)

        return item_id or ""

    def get(self, item_id: str) -> T | None:
        result = self._client.table(self._table).select("*").eq("id", item_id).limit(1).execute()
        if result.data:
            return self._model_class.model_validate(result.data[0])
        return None

    def list_all(self) -> list[T]:
        result = self._client.table(self._table).select("*").execute()
        return [self._model_class.model_validate(row) for row in result.data]

    def delete(self, item_id: str) -> bool:
        result = self._client.table(self._table).delete().eq("id", item_id).execute()
        return len(result.data) > 0


class JsonFileRepository(Repository[T]):
    """로컬 JSON 파일 기반 저장소 (폴백).

    data/{collection}/{id}.json 형태로 저장한다.
    Supabase 연결 불가 시 사용.
    """

    def __init__(self, base_dir: Path, collection: str, model_class: type[T]) -> None:
        self._dir = base_dir / collection
        self._dir.mkdir(parents=True, exist_ok=True)
        self._model_class = model_class

    def save(self, item: T) -> str:
        data = item.model_dump(mode="json")
        item_id = data.get("id") or str(uuid.uuid4())
        data["id"] = item_id
        file_path = self._dir / f"{item_id}.json"
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return item_id

    def get(self, item_id: str) -> T | None:
        file_path = self._dir / f"{item_id}.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return self._model_class.model_validate(data)

    def list_all(self) -> list[T]:
        items: list[T] = []
        for file_path in sorted(self._dir.glob("*.json")):
            data = json.loads(file_path.read_text(encoding="utf-8"))
            items.append(self._model_class.model_validate(data))
        return items

    def delete(self, item_id: str) -> bool:
        file_path = self._dir / f"{item_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
