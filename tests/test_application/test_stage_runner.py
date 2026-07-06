"""stage_runner 단위 테스트. 도메인 함수를 mock 하고 파일 저장 + reporter 호출 검증."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from application.progress import NullProgressReporter

# ── [3] 물리 추출 ──


class TestPhysicalExtraction:
    @patch("domain.analysis.physical_extractor.extract_physical")
    def test_saves_json_and_reports(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_analysis = MagicMock()
        mock_analysis.model_dump_json.return_value = '{"test": true}'
        mock_extract.return_value = mock_analysis

        page = MagicMock()
        page.idx = 0
        page.url = "https://m.blog.naver.com/test/123456789"

        from application.stage_runner import run_stage_physical_extraction

        reporter = MagicMock(spec=NullProgressReporter)
        results = run_stage_physical_extraction([page], "test", tmp_path, reporter)

        assert len(results) == 1
        assert (tmp_path / "analysis" / "physical" / "0.json").exists()
        reporter.stage_start.assert_called_once_with("physical_extraction", total=1)
        reporter.stage_end.assert_called_once()

    @patch("domain.analysis.physical_extractor.extract_physical")
    def test_skips_on_error(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.side_effect = ValueError("parse error")

        page = MagicMock()
        page.idx = 0
        page.url = "https://m.blog.naver.com/test/123456789"

        from application.stage_runner import run_stage_physical_extraction

        results = run_stage_physical_extraction([page], "test", tmp_path, NullProgressReporter())
        assert len(results) == 0


# ── [4a] 의미 추출 ──


class TestSemanticExtraction:
    @patch("domain.analysis.semantic_extractor.extract_semantic")
    def test_saves_per_page(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_result = MagicMock()
        mock_result.model_dump_json.return_value = '{"semantic": true}'
        mock_extract.return_value = mock_result

        page = MagicMock()
        page.idx = 0
        page.url = "https://m.blog.naver.com/test/123456789"

        physical = MagicMock()
        physical.url = page.url
        physical.title = "test title"
        physical.subtitle_count = 3

        from application.stage_runner import run_stage_semantic_extraction

        results = run_stage_semantic_extraction(
            [page], [physical], "kw", tmp_path, NullProgressReporter()
        )
        assert len(results) == 1
        assert (tmp_path / "analysis" / "semantic" / "0.json").exists()


# ── [4b] 소구 포인트 추출 ──


class TestAppealExtraction:
    @patch("domain.analysis.appeal_extractor.extract_appeal")
    def test_saves_per_page(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_result = MagicMock()
        mock_result.model_dump_json.return_value = '{"appeal": true}'
        mock_extract.return_value = mock_result

        page = MagicMock()
        page.idx = 0
        page.url = "https://m.blog.naver.com/test/123456789"

        physical = MagicMock()
        physical.url = page.url
        physical.title = "test"

        from application.stage_runner import run_stage_appeal_extraction

        results = run_stage_appeal_extraction(
            [page], [physical], "kw", tmp_path, NullProgressReporter()
        )
        assert len(results) == 1


# ── [5] 교차 분석 ──


class TestCrossAnalysis:
    @patch("domain.analysis.cross_analyzer.cross_analyze")
    @patch("application.stage_runner.save_pattern_card")
    def test_saves_pattern_card(
        self,
        mock_save: MagicMock,
        mock_cross: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_card = MagicMock()
        mock_card.analyzed_count = 8
        mock_cross.return_value = mock_card
        # Phase B7 — save_pattern_card 가 (path, supabase_id) tuple 반환.
        mock_save.return_value = (tmp_path / "analysis" / "pattern-card.json", "pc-uuid-1")

        from application.stage_runner import run_stage_cross_analysis

        reporter = MagicMock(spec=NullProgressReporter)
        card, pattern_card_id = run_stage_cross_analysis(
            "kw", "slug", [], [], [], tmp_path, reporter
        )
        assert card == mock_card
        assert pattern_card_id == "pc-uuid-1"
        mock_save.assert_called_once()

    @patch("domain.analysis.cross_analyzer.cross_analyze")
    @patch("application.stage_runner.save_pattern_card")
    def test_supabase_id_none_propagates(
        self,
        mock_save: MagicMock,
        mock_cross: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Supabase 미설정/실패 시 (path, None) — graceful."""
        mock_card = MagicMock()
        mock_cross.return_value = mock_card
        mock_save.return_value = (tmp_path / "analysis" / "pattern-card.json", None)

        from application.stage_runner import run_stage_cross_analysis

        _, pattern_card_id = run_stage_cross_analysis(
            "kw", "slug", [], [], [], tmp_path, MagicMock(spec=NullProgressReporter)
        )
        assert pattern_card_id is None


# ── [6] 아웃라인 생성 ──


class TestOutlineGeneration:
    @patch("domain.generation.title_validator.validate_title")
    @patch("domain.generation.outline_validator.validate_outline")
    @patch("domain.generation.outline_writer.generate_outline")
    @patch("domain.compliance.rules.build_pre_generation_injection")
    def test_saves_outline_json(
        self,
        mock_injection: MagicMock,
        mock_gen: MagicMock,
        mock_validate: MagicMock,
        mock_title_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_injection.return_value = "rules text"
        mock_validate.return_value = []  # no issues
        from domain.generation.title_validator import TitleValidationReport

        mock_title_validate.return_value = TitleValidationReport(passed=True, issues=[])
        mock_outline = MagicMock()
        mock_outline.title = "Test Title"
        mock_outline.sections = [MagicMock(), MagicMock()]
        mock_outline.image_prompts = [MagicMock()]
        mock_outline.model_dump_json.return_value = '{"title":"Test Title"}'
        mock_gen.return_value = mock_outline

        from application.stage_runner import run_stage_outline_generation

        result = run_stage_outline_generation(MagicMock(), tmp_path, NullProgressReporter())
        assert result == mock_outline
        assert (tmp_path / "content" / "outline.json").exists()

    @patch("domain.generation.title_validator.validate_title")
    @patch("domain.generation.outline_validator.validate_outline")
    @patch("domain.generation.outline_writer.generate_outline")
    @patch("domain.compliance.rules.build_pre_generation_injection")
    def test_retries_on_validation_issues(
        self,
        mock_injection: MagicMock,
        mock_gen: MagicMock,
        mock_validate: MagicMock,
        mock_title_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        """검증 실패 시 1회 재생성한다."""
        mock_injection.return_value = "rules text"

        from domain.generation.outline_validator import OutlineIssue
        from domain.generation.title_validator import TitleValidationReport

        mock_validate.return_value = [
            OutlineIssue(field="section_count", expected=">=5", actual="3")
        ]
        mock_title_validate.return_value = TitleValidationReport(passed=True, issues=[])
        mock_outline = MagicMock()
        mock_outline.title = "Retried Title"
        mock_outline.sections = [MagicMock()] * 5
        mock_outline.image_prompts = [MagicMock()]
        mock_outline.model_dump_json.return_value = '{"title":"Retried Title"}'
        mock_outline.model_copy.return_value = mock_outline  # _replace_intro 처리
        mock_gen.return_value = mock_outline

        from application.stage_runner import run_stage_outline_generation

        run_stage_outline_generation(MagicMock(), tmp_path, NullProgressReporter())
        assert mock_gen.call_count == 2


# ── [8] 컴플라이언스 ──


class TestComplianceCheck:
    @patch("domain.composer.assembler.assemble_content")
    @patch("domain.compliance.checker.check_compliance")
    def test_passes_clean_text(
        self,
        mock_check: MagicMock,
        mock_assemble: MagicMock,
        tmp_path: Path,
    ) -> None:
        assembled = MagicMock()
        assembled.content_md = "clean text"
        mock_assemble.return_value = assembled
        mock_check.return_value = []  # no violations

        from application.stage_runner import run_stage_compliance_check

        report = run_stage_compliance_check(
            MagicMock(), MagicMock(), tmp_path, NullProgressReporter()
        )
        assert report.passed is True
        assert (tmp_path / "content" / "compliance-report.json").exists()

    @patch("domain.composer.assembler.assemble_content")
    @patch("domain.compliance.checker.check_compliance")
    @patch("domain.compliance.fixer.fix_violations")
    def test_fix_and_recheck(
        self,
        mock_fix: MagicMock,
        mock_check: MagicMock,
        mock_assemble: MagicMock,
        tmp_path: Path,
    ) -> None:
        assembled = MagicMock()
        assembled.content_md = "bad text"
        mock_assemble.return_value = assembled

        from domain.compliance.model import ChangelogEntry

        violation = MagicMock()
        mock_check.side_effect = [[violation], []]  # 1st fails, 2nd passes
        entry = ChangelogEntry(
            section=1, before="bad", after="good", rule="test_rule", reason="fix"
        )
        mock_fix.return_value = ("fixed text", [entry])

        from application.stage_runner import run_stage_compliance_check

        report = run_stage_compliance_check(
            MagicMock(), MagicMock(), tmp_path, NullProgressReporter()
        )
        assert report.passed is True
        assert report.iterations == 2


# ── [9] 이미지 생성 ──


class TestImageGeneration:
    def test_skip_when_flag_disabled(self, tmp_path: Path) -> None:
        from application.stage_runner import run_stage_image_generation

        outline = MagicMock()
        outline.image_prompts = []

        result = run_stage_image_generation(
            outline,
            tmp_path,
            NullProgressReporter(),
            generate_images_flag=False,
        )
        assert len(result.generated) == 0
        assert len(result.skipped) == 0


# ── [10] 조립 ──


class TestCompose:
    @patch("application.stage_runner._save_generated_to_supabase")
    @patch("domain.composer.outline_md.convert_outline_to_md")
    @patch("domain.composer.naver_html.convert_to_naver_html")
    @patch("domain.composer.assembler.assemble_content")
    def test_saves_all_files(
        self,
        mock_assemble: MagicMock,
        mock_html: MagicMock,
        mock_outline_md: MagicMock,
        mock_save_supabase: MagicMock,
        tmp_path: Path,
    ) -> None:
        from domain.compliance.model import ComplianceReport

        assembled = MagicMock()
        assembled.content_md = "# Title\n\nContent"
        assembled.title = "Title"
        mock_assemble.return_value = assembled

        html_doc = MagicMock()
        html_doc.html = "<html></html>"
        mock_html.return_value = html_doc

        outline_md = MagicMock()
        outline_md.content = "# Outline"
        mock_outline_md.return_value = outline_md

        compliance = ComplianceReport(passed=True, iterations=1, final_text="")
        # Phase B7 — _save_generated_to_supabase 가 tuple 반환.
        mock_save_supabase.return_value = ("gen-uuid-1", "pc-uuid-1")

        from application.stage_runner import run_stage_compose

        result = run_stage_compose(
            MagicMock(),
            MagicMock(),
            compliance,
            None,
            tmp_path,
            NullProgressReporter(),
        )
        assert (tmp_path / "content" / "seo-content.md").exists()
        assert (tmp_path / "content" / "seo-content.html").exists()
        assert (tmp_path / "content" / "outline.md").exists()
        mock_save_supabase.assert_called_once()
        # Phase B7 — ComposeStageResult 가 회수된 두 id 를 동봉.
        assert result.generated_content_id == "gen-uuid-1"
        assert result.pattern_card_id == "pc-uuid-1"
        assert "seo_content_md" in result.paths


class TestMarkComplianceViolations:
    def test_banner_and_inline_marker(self) -> None:
        from application.stage_runner import _mark_compliance_violations
        from domain.compliance.model import ComplianceReport, Violation

        content_md = "# 제목\n\n본문 시작. 특정 위반 문구 여기있음. 뒷부분."
        report = ComplianceReport(
            passed=False,
            iterations=3,
            violations=[
                Violation(
                    category="first_person_promotion",
                    text_snippet="특정 위반 문구 여기있음",
                    section_index=2,
                    severity="medium",
                    reason="기관 홍보로 기능",
                )
            ],
            final_text=content_md,
        )

        marked_body, banner = _mark_compliance_violations(content_md, report)

        # banner 와 본문이 분리되어 반환 (2026-05-10) — 일괄 복사 시 banner 가 본문에 따라가지 않도록.
        assert banner.startswith("> ⚠️ **의료법 검증 미통과")
        assert "[first_person_promotion]" in banner
        # 인라인 마커는 본문에만 (사용자 수동 검수 가이드)
        assert "**⚠️ 특정 위반 문구 여기있음 ⚠️**" in marked_body
        assert "의료법 검증 미통과" not in marked_body

    def test_missing_snippet_keeps_banner(self) -> None:
        from application.stage_runner import _mark_compliance_violations
        from domain.compliance.model import ComplianceReport, Violation

        content_md = "# 제목\n\n본문."
        report = ComplianceReport(
            passed=False,
            iterations=3,
            violations=[
                Violation(
                    category="patient_testimonial",
                    text_snippet="본문에 존재하지 않는 스니펫",
                    severity="low",
                    reason="사유",
                )
            ],
            final_text=content_md,
        )

        marked_body, banner = _mark_compliance_violations(content_md, report)

        # snippet 매칭 실패해도 banner 는 카테고리 정보 유지
        assert "[patient_testimonial]" in banner
        # 본문은 인라인 래핑 없이 원본 그대로
        assert marked_body == content_md


# ── e2e 발견 이슈 #1: Storage key 한글 → ASCII slug ────────────────────────


class TestAsciiSafeSlug:
    """Supabase Storage 의 InvalidKey 회피 — 비-ASCII 키워드를 hash slug 로 변환."""

    def test_ascii_only_name_preserved(self):
        from application.stage_runner import _ascii_safe_slug

        assert _ascii_safe_slug("hair-care") == "hair-care"
        assert _ascii_safe_slug("test_123") == "test_123"
        assert _ascii_safe_slug("seo.text") == "seo.text"

    def test_korean_keyword_hashed(self):
        from application.stage_runner import _ascii_safe_slug

        result = _ascii_safe_slug("다이어트한의원")
        assert result.startswith("kw-")
        assert len(result) == 15  # "kw-" + 12 hex
        assert result.replace("kw-", "").isalnum()

    def test_korean_keyword_deterministic(self):
        from application.stage_runner import _ascii_safe_slug

        # 같은 입력 → 같은 hash
        a = _ascii_safe_slug("다이어트한의원")
        b = _ascii_safe_slug("다이어트한의원")
        assert a == b

    def test_storage_prefix_korean(self, tmp_path):
        from application.stage_runner import _storage_prefix

        # output/{한글 slug}/{ts}/ 경로
        output_dir = tmp_path / "다이어트한의원" / "20260506-143336"
        output_dir.mkdir(parents=True)
        prefix = _storage_prefix(output_dir)
        # ASCII-safe 가 보장되어야 함
        assert prefix.startswith("kw-")
        assert "/20260506-143336" in prefix
        assert prefix.isascii()


# ── 본문 fetcher 라우팅 팩토리 (PR4) ─────────────────────────────────────────


class TestBodyFetcherRouting:
    """`_build_body_fetcher()` 토글 분기 검증.

    본문([2]) 경로는 `crawler_body_fetcher` 토글의 영향을 받는다. `_build_brightdata_client()`
    원시 팩토리는 토글과 무관하게 항상 BrightDataClient (SERP·본문 폴백 공용).
    """

    def _stub_bright_data_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """폴백/SERP 용 BrightDataClient 생성에 필요한 키를 더미로 주입."""
        from config.settings import settings

        monkeypatch.setattr(settings, "bright_data_api_key", "dummy-key")
        monkeypatch.setattr(settings, "bright_data_web_unlocker_zone", "dummy-zone")

    def test_insane_returns_fallback_with_insane_primary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from application.stage_runner import _build_body_fetcher
        from config.settings import settings
        from domain.crawler.brightdata_client import BrightDataClient
        from domain.crawler.fallback_fetcher import FallbackFetcher
        from domain.crawler.insane_fetcher import InsaneFetcher

        self._stub_bright_data_keys(monkeypatch)
        monkeypatch.setattr(settings, "crawler_body_fetcher", "insane")

        fetcher = _build_body_fetcher()
        assert isinstance(fetcher, FallbackFetcher)
        # primary = InsaneFetcher, fallback = BrightDataClient
        assert isinstance(fetcher._primary, InsaneFetcher)
        assert isinstance(fetcher._fallback, BrightDataClient)

    def test_brightdata_returns_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from application.stage_runner import _build_body_fetcher
        from config.settings import settings
        from domain.crawler.brightdata_client import BrightDataClient

        self._stub_bright_data_keys(monkeypatch)
        monkeypatch.setattr(settings, "crawler_body_fetcher", "brightdata")

        fetcher = _build_body_fetcher()
        assert isinstance(fetcher, BrightDataClient)

    def test_brightdata_primitive_always_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`_build_brightdata_client()` 원시 팩토리는 토글과 무관하게 항상 BrightDataClient."""
        from application.stage_runner import _build_brightdata_client
        from config.settings import settings
        from domain.crawler.brightdata_client import BrightDataClient

        self._stub_bright_data_keys(monkeypatch)
        monkeypatch.setattr(settings, "crawler_body_fetcher", "insane")

        assert isinstance(_build_brightdata_client(), BrightDataClient)


# ── SERP fetcher 라우팅 팩토리 (PR-S2) ───────────────────────────────────────


class TestSerpFetcherRouting:
    """`_build_serp_fetcher()` 토글 분기 검증.

    분석 트랙 SERP([1]) + keyword_difficulty 난이도 SERP 가 `crawler_serp_fetcher` 토글로
    라우팅된다. "insane" = FallbackFetcher(InsaneFetcher desktop+#main_pack → BrightDataClient),
    "brightdata" = BrightDataClient 단독(롤백 밸브).
    """

    def _stub_bright_data_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from config.settings import settings

        monkeypatch.setattr(settings, "bright_data_api_key", "dummy-key")
        monkeypatch.setattr(settings, "bright_data_web_unlocker_zone", "dummy-zone")

    def test_insane_returns_fallback_with_tuned_insane_primary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from application.stage_runner import _SERP_SUCCESS_SELECTOR, _build_serp_fetcher
        from config.settings import settings
        from domain.crawler.brightdata_client import BrightDataClient
        from domain.crawler.fallback_fetcher import FallbackFetcher
        from domain.crawler.insane_fetcher import InsaneFetcher

        self._stub_bright_data_keys(monkeypatch)
        monkeypatch.setattr(settings, "crawler_serp_fetcher", "insane")

        fetcher = _build_serp_fetcher()
        assert isinstance(fetcher, FallbackFetcher)
        # primary = InsaneFetcher (desktop + #main_pack 튜닝), fallback = BrightDataClient
        assert isinstance(fetcher._primary, InsaneFetcher)
        assert isinstance(fetcher._fallback, BrightDataClient)
        assert fetcher._primary._device_class == "desktop"
        assert fetcher._primary._success_selectors == [_SERP_SUCCESS_SELECTOR]
        assert _SERP_SUCCESS_SELECTOR == "#main_pack"

    def test_brightdata_returns_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from application.stage_runner import _build_serp_fetcher
        from config.settings import settings
        from domain.crawler.brightdata_client import BrightDataClient

        self._stub_bright_data_keys(monkeypatch)
        monkeypatch.setattr(settings, "crawler_serp_fetcher", "brightdata")

        fetcher = _build_serp_fetcher()
        assert isinstance(fetcher, BrightDataClient)
