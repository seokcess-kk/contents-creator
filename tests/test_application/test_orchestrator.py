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
