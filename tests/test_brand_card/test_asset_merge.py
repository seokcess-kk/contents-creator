"""asset_merge — SPEC §6 입력 우선순위 5단계 병합 단위 테스트."""

from __future__ import annotations

from domain.brand_card.asset_merge import MergedAssets, merge_assets
from domain.brand_card.model import BrandMessageSource, CardCampaignInput


def _src(
    src_id: str,
    *,
    source_type: str = "brand_common",
    file_name: str | None = None,
    content: str | None = None,
) -> BrandMessageSource:
    return BrandMessageSource(
        id=src_id,
        brand_id="b-1",
        source_type=source_type,
        file_name=file_name,
        content_text=content,
    )


class TestMergeAssetsEmpty:
    def test_no_inputs_returns_empty(self) -> None:
        result = merge_assets(
            campaign_input=None,
            attached_sources=[],
            brand_sources=[],
        )
        assert result == MergedAssets()

    def test_campaign_only_no_sources(self) -> None:
        ci = CardCampaignInput(
            brand_id="b-1",
            keyword="다이어트",
            brief_text="강조: 체질 분석",
            required_phrases=["대구 동성로"],
            forbidden_phrases=["100% 보장"],
        )
        result = merge_assets(
            campaign_input=ci,
            attached_sources=[],
            brand_sources=[],
        )
        assert result.user_brief == "강조: 체질 분석"
        assert result.required_phrases == ["대구 동성로"]
        assert result.forbidden_phrases == ["100% 보장"]
        assert result.attached_files == []
        assert result.brand_common == []


class TestPriorityPartitioning:
    def test_attached_files_take_priority_over_brand_common(self) -> None:
        """attached_source 는 우선순위 2, brand_common 은 3 — 분리되어야."""
        attached = _src("s-1", source_type="brand_common", content="첨부 본문")
        brand = _src("s-2", source_type="brand_common", content="공통 자산")
        result = merge_assets(
            campaign_input=None,
            attached_sources=[attached],
            brand_sources=[attached, brand],  # attached 도 brand 전체 목록 안에 포함
        )
        # attached_files 에는 attached 만, brand_common 에는 attached 제외 후
        assert any("첨부 본문" in t for t in result.attached_files)
        assert any("공통 자산" in t for t in result.brand_common)
        # attached 가 brand_common 에 중복 등장하지 않아야
        assert not any("첨부 본문" in t for t in result.brand_common)

    def test_non_brand_common_sources_in_other_references(self) -> None:
        campaign_src = _src("s-3", source_type="campaign", content="캠페인 자산")
        keyword_src = _src("s-4", source_type="keyword_specific", content="키워드 자산")
        ref_src = _src("s-5", source_type="reference", content="참고 자산")
        result = merge_assets(
            campaign_input=None,
            attached_sources=[],
            brand_sources=[campaign_src, keyword_src, ref_src],
        )
        assert len(result.other_references) == 3
        assert result.brand_common == []

    def test_empty_content_skipped(self) -> None:
        empty_src = _src("s-6", content=None)
        full_src = _src("s-7", content="실제 내용")
        result = merge_assets(
            campaign_input=None,
            attached_sources=[],
            brand_sources=[empty_src, full_src],
        )
        # empty_src 는 제외
        assert len(result.brand_common) == 1
        assert "실제 내용" in result.brand_common[0]


class TestSourceTextLabel:
    def test_uses_file_name_when_present(self) -> None:
        src = _src(
            "s-1",
            source_type="brand_common",
            file_name="brochure.pdf",
            content="브로슈어 텍스트",
        )
        result = merge_assets(
            campaign_input=None,
            attached_sources=[],
            brand_sources=[src],
        )
        assert "[brochure.pdf]" in result.brand_common[0]

    def test_falls_back_to_source_type_when_no_filename(self) -> None:
        src = _src("s-1", source_type="reference", content="텍스트")
        result = merge_assets(
            campaign_input=None,
            attached_sources=[],
            brand_sources=[src],
        )
        assert "[reference]" in result.other_references[0]
