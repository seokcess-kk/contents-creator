"""저장소 추상화. MVP는 JsonFileRepository, 추후 Supabase 전환."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


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


class JsonFileRepository(Repository[T]):
    """로컬 JSON 파일 기반 저장소.

    data/{collection}/{id}.json 형태로 저장한다.
    Supabase 미생성 기간 동안 사용하는 MVP 구현.
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
