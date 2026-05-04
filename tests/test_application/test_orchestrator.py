"""orchestrator 통합 테스트. 모든 도메인 함수를 mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from application.models import StageStatus
from application.orchestrator import _slugify, run_analyze_only, run_pipeline, run_validate_only
from application.progress import NullProgressReporter

# ── slugify ──


class TestSlugify:
    def test_korean_preserved(self) -> None:
        assert _slugify("강남 다이어트 한의원") == "강남-다이어트-한의원"

    def test_whitespace_collapsed(self) -> None:
        assert _slugify("  a   b  ") == "a-b"

    def test_special_chars_removed(self) -> None:
        assert _slugify("test!@#$%keyword") == "testkeyword"

    def test_max_length(self) -> None:
        long = "가" * 100
        assert len(_slugify(long)) <= 80

    def test_empty_fallback(self) -> None:
        assert _slugify("!!!") == "unknown"


# ── run_pipeline ──


class TestRunPipeline:
    @patch("application.orchestrator._run_generation_stages")
    @patch("application.orchestrator._run_analysis_stages")
    @patch("application.orchestrator._update_latest_link")
    @patch("application.orchestrator._create_output_dir")
    def test_full_success(
        self,
        mock_output: MagicMock,
        mock_link: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        tmp_path: Path,
    ) -> None:
        from application.models import AnalyzeResult, GenerateResult

        mock_output.return_value = tmp_path
        mock_analyze.return_value = (
            AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="test",
                slug="test",
                analyzed_count=8,
            ),
            MagicMock(),  # pattern card
        )
        mock_generate.return_value = GenerateResult(
            status=StageStatus.SUCCEEDED,
            keyword="test",
            slug="test",
            compliance_passed=True,
        )

        result = run_pipeline("test", reporter=NullProgressReporter())
        assert result.status == StageStatus.SUCCEEDED
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()

    @patch("application.orchestrator._run_generation_stages")
    @patch("application.orchestrator._run_analysis_stages")
    @patch("application.orchestrator._update_latest_link")
    @patch("application.orchestrator._create_output_dir")
    def test_pipeline_result_propagates_supabase_ids(
        self,
        mock_output: MagicMock,
        mock_link: MagicMock,
        mock_analyze: MagicMock,
        mock_generate: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Phase B7 — PipelineResult 에 두 id 채워짐."""
        from application.models import AnalyzeResult, GenerateResult

        mock_output.return_value = tmp_path
        mock_analyze.return_value = (
            AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="test",
                slug="test",
                analyzed_count=8,
                pattern_card_id="pc-from-analysis",
            ),
            MagicMock(),
        )
        mock_generate.return_value = GenerateResult(
            status=StageStatus.SUCCEEDED,
            keyword="test",
            slug="test",
            pattern_card_id="pc-from-compose",
            generated_content_id="gen-from-compose",
        )
        result = run_pipeline("test", reporter=NullProgressReporter())
        # generation 단계의 두 id 가 PipelineResult 로 전파.
        assert result.pattern_card_id == "pc-from-compose"
        assert result.generated_content_id == "gen-from-compose"

    @patch("application.orchestrator._run_analysis_stages")
    @patch("application.orchestrator._create_output_dir")
    def test_analysis_failure_stops_pipeline(
        self,
        mock_output: MagicMock,
        mock_analyze: MagicMock,
        tmp_path: Path,
    ) -> None:
        from application.models import AnalyzeResult

        mock_output.return_value = tmp_path
        mock_analyze.return_value = (
            AnalyzeResult(
                status=StageStatus.FAILED,
                keyword="test",
                slug="test",
                error="SERP 수집 실패",
            ),
            None,
        )

        result = run_pipeline("test", reporter=NullProgressReporter())
        assert result.status == StageStatus.FAILED
        assert "SERP" in (result.error or "")

    @patch("application.orchestrator._run_generation_stages")
    @patch("application.orchestrator._update_latest_link")
    @patch("application.orchestrator._create_output_dir")
    def test_with_pattern_card_path(
        self,
        mock_output: MagicMock,
        mock_link: MagicMock,
        mock_generate: MagicMock,
        tmp_path: Path,
    ) -> None:
        from application.models import GenerateResult

        mock_output.return_value = tmp_path

        # 패턴 카드 파일 생성
        card_path = tmp_path / "pattern-card.json"
        card_path.write_text(
            '{"schema_version":"2.0","keyword":"test","slug":"test","analyzed_count":8,"stats":{"chars":{"avg":2800,"min":2000,"max":3500},"subtitles":{"avg":5,"min":3,"max":7},"keyword_density":{"avg":0.01,"min":0.005,"max":0.02},"subtitle_keyword_ratio":0.6,"first_keyword_sentence":2,"paragraph_avg_chars":90}}'
        )

        mock_generate.return_value = GenerateResult(
            status=StageStatus.SUCCEEDED,
            keyword="test",
            slug="test",
        )

        result = run_pipeline(
            "test",
            reporter=NullProgressReporter(),
            pattern_card_path=card_path,
        )
        assert result.status == StageStatus.SUCCEEDED
        mock_generate.assert_called_once()


# ── run_analyze_only ──


class TestRunAnalyzeOnly:
    @patch("application.orchestrator._run_analysis_stages")
    @patch("application.orchestrator._update_latest_link")
    @patch("application.orchestrator._create_output_dir")
    def test_success(
        self,
        mock_output: MagicMock,
        mock_link: MagicMock,
        mock_analyze: MagicMock,
        tmp_path: Path,
    ) -> None:
        from application.models import AnalyzeResult

        mock_output.return_value = tmp_path
        mock_analyze.return_value = (
            AnalyzeResult(
                status=StageStatus.SUCCEEDED,
                keyword="test",
                slug="test",
                analyzed_count=8,
            ),
            MagicMock(),
        )

        result = run_analyze_only("test", reporter=NullProgressReporter())
        assert result.status == StageStatus.SUCCEEDED


# ── run_validate_only ──


class TestRunValidateOnly:
    @patch("domain.compliance.checker.check_compliance")
    def test_clean_content_passes(
        self,
        mock_check: MagicMock,
        tmp_path: Path,
    ) -> None:
        content = tmp_path / "test.md"
        content.write_text("안전한 콘텐츠입니다.", encoding="utf-8")
        mock_check.return_value = []

        result = run_validate_only(content, reporter=NullProgressReporter())
        assert result.passed is True

    def test_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.md"
        result = run_validate_only(missing, reporter=NullProgressReporter())
        assert result.status == StageStatus.FAILED
        assert "파일 없음" in (result.error or "")


# ── run_brand_card_only / run_full_package ──


class TestRunBrandCardOnly:
    """SPEC-BRAND-CARD §15 [B1]~[B5] 단독 트랙 — mock 으로 도메인 격리."""

    def _fake_plan(self, plan_id: str = "p1", reuse: str = "rg1") -> object:
        from domain.brand_card.model import BrandCardPlan

        return BrandCardPlan(
            id=plan_id,
            brand_id="b1",
            keyword="다이어트",
            template_id="diet_empathy",
            strategy="empathy_first",
            expression_level="balanced",
            angle="공감 우선",
            blocks=[],
            status="draft",
            reuse_group_id=reuse,
        )

    @patch("application.brand_card_orchestrator.generate_card_plan")
    def test_draft_mode_returns_succeeded(self, mock_gen: MagicMock) -> None:
        from application.orchestrator import run_brand_card_only

        mock_gen.return_value = [self._fake_plan("p1"), self._fake_plan("p2")]
        result = run_brand_card_only(
            brand_id="b1", keyword="다이어트", reporter=NullProgressReporter()
        )
        assert result.status == StageStatus.SUCCEEDED
        assert result.plan_count == 2
        assert result.reuse_group_id == "rg1"
        assert result.rendered_count == 0  # auto_approve 아니므로 렌더 X

    @patch("application.brand_card_orchestrator.generate_card_plan")
    def test_zero_plans_failed(self, mock_gen: MagicMock) -> None:
        from application.orchestrator import run_brand_card_only

        mock_gen.return_value = []
        result = run_brand_card_only(
            brand_id="b1", keyword="다이어트", reporter=NullProgressReporter()
        )
        assert result.status == StageStatus.FAILED
        assert "0개" in (result.error or "")

    @patch("application.brand_card_orchestrator.generate_card_plan")
    def test_card_plan_exception(self, mock_gen: MagicMock) -> None:
        from application.orchestrator import run_brand_card_only

        mock_gen.side_effect = RuntimeError("LLM 실패")
        result = run_brand_card_only(
            brand_id="b1", keyword="다이어트", reporter=NullProgressReporter()
        )
        assert result.status == StageStatus.FAILED
        assert "LLM 실패" in (result.error or "")

    @patch("application.brand_card_orchestrator.render_card_set")
    @patch("application.brand_card_orchestrator.approve_plan")
    @patch("application.brand_card_orchestrator.generate_card_plan")
    def test_auto_approve_renders(
        self,
        mock_gen: MagicMock,
        mock_approve: MagicMock,
        mock_render: MagicMock,
        tmp_path: Path,
    ) -> None:
        from application.orchestrator import run_brand_card_only
        from domain.brand_card.model import RenderedCardSet

        plans = [self._fake_plan("p1"), self._fake_plan("p2")]
        mock_gen.return_value = plans
        manifest_path = tmp_path / "rg1" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text("{}", encoding="utf-8")
        mock_render.return_value = RenderedCardSet(
            reuse_group_id="rg1",
            brand_id="b1",
            keyword="다이어트",
            cards=[],
            manifest_path=manifest_path,
        )

        result = run_brand_card_only(
            brand_id="b1",
            keyword="다이어트",
            auto_approve=True,
            output_root=tmp_path,
            reporter=NullProgressReporter(),
        )
        assert result.status == StageStatus.SUCCEEDED
        assert result.plan_count == 2
        assert result.manifest_path == manifest_path
        assert mock_approve.call_count == 2  # 두 plan 모두 approve


class TestRunFullPackage:
    """SEO + 브랜드 카드 병렬 합류."""

    @patch("application.orchestrator.run_brand_card_only")
    @patch("application.orchestrator.run_pipeline")
    def test_both_succeed(self, mock_seo: MagicMock, mock_brand: MagicMock, tmp_path: Path) -> None:
        from application.models import BrandCardResult, PipelineResult
        from application.orchestrator import run_full_package

        mock_seo.return_value = PipelineResult(
            status=StageStatus.SUCCEEDED, keyword="다이어트", slug="다이어트"
        )
        mock_brand.return_value = BrandCardResult(
            status=StageStatus.SUCCEEDED,
            brand_id="b1",
            keyword="다이어트",
            reuse_group_id="rg1",
            plan_count=3,
        )
        result = run_full_package(
            keyword="다이어트", brand_id="b1", reporter=NullProgressReporter()
        )
        assert result.status == StageStatus.SUCCEEDED
        assert result.seo_result is not None and result.seo_result.status == StageStatus.SUCCEEDED
        assert result.brand_card_result is not None
        assert result.brand_card_result.plan_count == 3

    @patch("application.orchestrator.run_brand_card_only")
    @patch("application.orchestrator.run_pipeline")
    def test_seo_fails_brand_succeeds_partial(
        self, mock_seo: MagicMock, mock_brand: MagicMock
    ) -> None:
        from application.models import BrandCardResult, PipelineResult
        from application.orchestrator import run_full_package

        mock_seo.return_value = PipelineResult(
            status=StageStatus.FAILED, keyword="다이어트", slug="다이어트", error="크롤 실패"
        )
        mock_brand.return_value = BrandCardResult(
            status=StageStatus.SUCCEEDED, brand_id="b1", keyword="다이어트", plan_count=2
        )
        result = run_full_package(
            keyword="다이어트", brand_id="b1", reporter=NullProgressReporter()
        )
        # 한쪽 성공·한쪽 실패 → 부분 성공으로 SUCCEEDED 반환 (데이터로는 둘 다 보존)
        assert result.status == StageStatus.SUCCEEDED
        assert result.seo_result is not None and result.seo_result.status == StageStatus.FAILED
        assert result.brand_card_result is not None
        assert result.brand_card_result.status == StageStatus.SUCCEEDED

    @patch("application.orchestrator.run_brand_card_only")
    @patch("application.orchestrator.run_pipeline")
    def test_both_fail_overall_failed(self, mock_seo: MagicMock, mock_brand: MagicMock) -> None:
        from application.models import BrandCardResult, PipelineResult
        from application.orchestrator import run_full_package

        mock_seo.return_value = PipelineResult(
            status=StageStatus.FAILED, keyword="다이어트", slug="다이어트"
        )
        mock_brand.return_value = BrandCardResult(
            status=StageStatus.FAILED, brand_id="b1", keyword="다이어트"
        )
        result = run_full_package(
            keyword="다이어트", brand_id="b1", reporter=NullProgressReporter()
        )
        assert result.status == StageStatus.FAILED

    @patch("application.orchestrator.run_brand_card_only")
    @patch("application.orchestrator.run_pipeline")
    def test_seo_exception_data_preserved(self, mock_seo: MagicMock, mock_brand: MagicMock) -> None:
        from application.models import BrandCardResult
        from application.orchestrator import run_full_package

        mock_seo.side_effect = RuntimeError("network down")
        mock_brand.return_value = BrandCardResult(
            status=StageStatus.SUCCEEDED, brand_id="b1", keyword="다이어트", plan_count=1
        )
        result = run_full_package(
            keyword="다이어트", brand_id="b1", reporter=NullProgressReporter()
        )
        assert result.seo_result is None
        assert result.brand_card_result is not None
        assert "network down" in (result.error or "")
