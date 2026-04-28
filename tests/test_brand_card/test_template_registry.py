"""template_registry — meta.json 로드 + card_type 호환성 검증."""

from __future__ import annotations

import pytest

from domain.brand_card.template_registry import (
    TemplateMeta,
    TemplateNotFoundError,
    get_template,
    list_templates,
    validate_card_type_compat,
)


class TestGetTemplate:
    def test_clinic_trust_loads(self) -> None:
        meta = get_template("clinic_trust")
        assert isinstance(meta, TemplateMeta)
        assert meta.template_id == "clinic_trust"
        assert meta.width_px == 1080
        assert meta.height_px == 1350
        assert "hero" in meta.supported_card_types
        assert "trust_closing" in meta.supported_card_types

    def test_clinic_trust_files_exist(self) -> None:
        meta = get_template("clinic_trust")
        assert meta.card_html_path.exists()
        assert meta.style_css_path.exists()

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(TemplateNotFoundError, match="meta.json 미존재"):
            get_template("unknown_template")


class TestListTemplates:
    def test_includes_clinic_trust(self) -> None:
        templates = list_templates()
        ids = {t.template_id for t in templates}
        assert "clinic_trust" in ids

    def test_all_have_dimensions(self) -> None:
        for t in list_templates():
            assert t.width_px > 0
            assert t.height_px > 0


class TestValidateCardTypeCompat:
    def test_compatible_types_return_empty(self) -> None:
        meta = get_template("clinic_trust")
        incompat = validate_card_type_compat(meta, ["hero", "problem", "solution"])
        assert incompat == []

    def test_unsupported_types_returned(self) -> None:
        meta = get_template("clinic_trust")
        incompat = validate_card_type_compat(meta, ["hero", "unknown_type"])
        assert "unknown_type" in incompat
        assert "hero" not in incompat

    def test_all_six_p1_card_types_supported(self) -> None:
        """SPEC §4 P1 6 card type 모두 clinic_trust 가 지원."""
        meta = get_template("clinic_trust")
        all_types = [
            "hero",
            "problem",
            "solution",
            "differentiator",
            "process",
            "trust_closing",
        ]
        assert validate_card_type_compat(meta, all_types) == []
