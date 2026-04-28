"""template_registry — meta.json 로드 + card_type 호환성 검증.

P1 4 템플릿 (clinic_trust / diet_empathy / process_guide / local_info) 모두
parametrize 로 동일 검증을 수행. SPEC §10 표 1:1 매핑.
"""

from __future__ import annotations

import pytest

from domain.brand_card.template_registry import (
    TemplateMeta,
    TemplateNotFoundError,
    get_template,
    list_templates,
    validate_card_type_compat,
)

# SPEC §10 P1 4 템플릿 — 신규 추가 시 본 상수 + meta.json 동시 갱신.
P1_TEMPLATE_IDS = ("clinic_trust", "diet_empathy", "process_guide", "local_info")
P1_CARD_TYPES = (
    "hero",
    "problem",
    "solution",
    "differentiator",
    "process",
    "trust_closing",
)


class TestGetTemplate:
    @pytest.mark.parametrize("template_id", P1_TEMPLATE_IDS)
    def test_loads(self, template_id: str) -> None:
        meta = get_template(template_id)
        assert isinstance(meta, TemplateMeta)
        assert meta.template_id == template_id
        assert meta.width_px == 1080
        assert meta.height_px == 1350

    @pytest.mark.parametrize("template_id", P1_TEMPLATE_IDS)
    def test_files_exist(self, template_id: str) -> None:
        meta = get_template(template_id)
        assert meta.card_html_path.exists()
        assert meta.style_css_path.exists()

    @pytest.mark.parametrize("template_id", P1_TEMPLATE_IDS)
    def test_meta_has_human_fields(self, template_id: str) -> None:
        """name·description 은 UI 표시용 — 비어있으면 안 됨."""
        meta = get_template(template_id)
        assert meta.name.strip()
        assert meta.description.strip()

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(TemplateNotFoundError, match="meta.json 미존재"):
            get_template("unknown_template")


class TestListTemplates:
    def test_includes_all_p1_templates(self) -> None:
        templates = list_templates()
        ids = {t.template_id for t in templates}
        for tid in P1_TEMPLATE_IDS:
            assert tid in ids, f"missing template: {tid}"

    def test_all_have_dimensions(self) -> None:
        for t in list_templates():
            assert t.width_px > 0
            assert t.height_px > 0


class TestValidateCardTypeCompat:
    @pytest.mark.parametrize("template_id", P1_TEMPLATE_IDS)
    def test_supports_all_p1_card_types(self, template_id: str) -> None:
        """SPEC §4 P1 6 card type 모두 4 템플릿이 지원."""
        meta = get_template(template_id)
        assert validate_card_type_compat(meta, list(P1_CARD_TYPES)) == []

    def test_unsupported_types_returned(self) -> None:
        meta = get_template("clinic_trust")
        incompat = validate_card_type_compat(meta, ["hero", "unknown_type"])
        assert "unknown_type" in incompat
        assert "hero" not in incompat

    def test_compatible_types_return_empty(self) -> None:
        meta = get_template("clinic_trust")
        incompat = validate_card_type_compat(meta, ["hero", "problem", "solution"])
        assert incompat == []
