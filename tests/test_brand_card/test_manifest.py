"""manifest — cards-manifest.json 빌더 단위 테스트."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from domain.brand_card.manifest import build_manifest, write_manifest
from domain.brand_card.model import RenderedBrandCard


def _card(
    variant_idx: int = 1,
    template_id: str = "clinic_trust",
    strategy: str = "trust_first",
    png_name: str = "card-clinic_trust-trust_first-01.png",
    compliance_passed: bool = True,
) -> RenderedBrandCard:
    return RenderedBrandCard(
        brand_id="b-1",
        keyword="다이어트한의원",
        strategy=strategy,
        expression_level="balanced",
        template_id=template_id,
        variant_idx=variant_idx,
        png_path=Path(png_name),
        width_px=1080,
        height_px=1350,
        compliance_report={"passed": compliance_passed},
    )


class TestBuildManifest:
    def test_includes_brand_keyword_timestamp(self) -> None:
        ts = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)
        m = build_manifest(
            brand_id="b-1",
            keyword="다이어트한의원",
            cards=[_card()],
            generated_at=ts,
        )
        assert m["brand_id"] == "b-1"
        assert m["keyword"] == "다이어트한의원"
        assert m["generated_at"].startswith("2026-04-28")

    def test_card_entries_match_spec(self) -> None:
        m = build_manifest(
            brand_id="b-1",
            keyword="kw",
            cards=[
                _card(variant_idx=1, png_name="card-clinic_trust-trust_first-01.png"),
                _card(variant_idx=2, png_name="card-clinic_trust-trust_first-02.png"),
            ],
        )
        cards = m["cards"]
        assert isinstance(cards, list)
        assert len(cards) == 2
        first = cards[0]
        assert first["template_id"] == "clinic_trust"
        assert first["strategy"] == "trust_first"
        assert first["variant_idx"] == 1
        assert first["path"] == "card-clinic_trust-trust_first-01.png"
        assert first["compliance_passed"] is True

    def test_compliance_failed_reflected(self) -> None:
        m = build_manifest(
            brand_id="b-1",
            keyword="kw",
            cards=[_card(compliance_passed=False)],
        )
        cards = m["cards"]
        assert isinstance(cards, list)
        assert cards[0]["compliance_passed"] is False


class TestWriteManifest:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        out = write_manifest(
            output_dir=tmp_path,
            brand_id="b-1",
            keyword="kw",
            cards=[_card()],
        )
        assert out.exists()
        assert out.name == "cards-manifest.json"
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["brand_id"] == "b-1"
        assert loaded["cards"][0]["template_id"] == "clinic_trust"

    def test_korean_preserved_in_json(self, tmp_path: Path) -> None:
        out = write_manifest(
            output_dir=tmp_path,
            brand_id="b-1",
            keyword="다이어트한의원",
            cards=[],
        )
        text = out.read_text(encoding="utf-8")
        assert "다이어트한의원" in text  # ensure_ascii=False 보장
