"""브랜드 카드 템플릿 레지스트리 — meta.json 로드 + 호환성 검증.

각 템플릿은 디렉토리 1개:
  domain/brand_card/templates/{template_id}/
    ├── card.html.j2  ← Jinja2 (CardBlock 1개를 받음)
    ├── style.css     ← @font-face + 카드 스타일
    └── meta.json     ← {template_id, supported_card_types, dimensions}

P1 4 템플릿: clinic_trust / diet_empathy / process_guide / local_info.
프론트엔드-design 스킬로 prototyping 후 정적 동결 (D4).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from domain.brand_card.model import BrandCardError

logger = logging.getLogger(__name__)


_TEMPLATES_ROOT = Path(__file__).parent / "templates"


class TemplateNotFoundError(BrandCardError):
    """template_id 디렉토리 또는 meta.json 미존재."""


@dataclass(frozen=True)
class TemplateMeta:
    """템플릿 메타 — meta.json 파일에서 로드."""

    template_id: str
    name: str
    description: str
    supported_card_types: list[str]
    width_px: int
    height_px: int
    template_dir: Path

    @property
    def card_html_path(self) -> Path:
        return self.template_dir / "card.html.j2"

    @property
    def style_css_path(self) -> Path:
        return self.template_dir / "style.css"


def get_template(template_id: str) -> TemplateMeta:
    """template_id 로 메타 로드. 미존재 시 TemplateNotFoundError."""
    template_dir = _TEMPLATES_ROOT / template_id
    meta_path = template_dir / "meta.json"
    if not meta_path.exists():
        raise TemplateNotFoundError(f"template_id={template_id!r} 의 meta.json 미존재: {meta_path}")
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    return TemplateMeta(
        template_id=raw["template_id"],
        name=raw["name"],
        description=raw["description"],
        supported_card_types=list(raw["supported_card_types"]),
        width_px=int(raw["width_px"]),
        height_px=int(raw["height_px"]),
        template_dir=template_dir,
    )


def list_templates() -> list[TemplateMeta]:
    """등록된 모든 템플릿 메타 — UI 선택 화면용."""
    if not _TEMPLATES_ROOT.exists():
        return []
    out: list[TemplateMeta] = []
    for child in _TEMPLATES_ROOT.iterdir():
        if not child.is_dir():
            continue
        if (child / "meta.json").exists():
            try:
                out.append(get_template(child.name))
            except Exception:
                logger.warning("template.meta_load_failed dir=%s", child, exc_info=True)
    return out


def validate_card_type_compat(meta: TemplateMeta, card_types: list[str]) -> list[str]:
    """plan 의 card_types 가 템플릿이 지원하는지 검증.

    Returns: 호환 안 되는 card_type 목록 (빈 리스트면 모두 호환).
    """
    supported = set(meta.supported_card_types)
    return [ct for ct in card_types if ct not in supported]
