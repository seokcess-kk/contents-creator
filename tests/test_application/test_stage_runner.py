"""stage_runner 단위 테스트. 도메인 함수를 mock 하고 파일 저장 + reporter 호출 검증."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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
        mock_save.return_value = tmp_path / "analysis" / "pattern-card.json"

        from application.stage_runner import run_stage_cross_analysis

        reporter = MagicMock(spec=NullProgressReporter)
        result = run_stage_cross_analysis("kw", "slug", [], [], [], tmp_path, reporter)
        assert result == mock_card
        mock_save.assert_called_once()


# ── [6] 아웃라인 생성 ──


class TestOutlineGeneration:
    @patch("domain.generation.outline_validator.validate_outline")
    @patch("domain.generation.outline_writer.generate_outline")
    @patch("domain.compliance.rules.build_pre_generation_injection")
    def test_saves_outline_json(
        self,
        mock_injection: MagicMock,
        mock_gen: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_injection.return_value = "rules text"
        mock_validate.return_value = []  # no issues
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

    @patch("domain.generation.outline_validator.validate_outline")
    @patch("domain.generation.outline_writer.generate_outline")
    @patch("domain.compliance.rules.build_pre_generation_injection")
    def test_retries_on_validation_issues(
        self,
        mock_injection: MagicMock,
        mock_gen: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        """검증 실패 시 1회 재생성한다."""
        mock_injection.return_value = "rules text"

        from domain.generation.outline_validator import OutlineIssue

        mock_validate.return_value = [
            OutlineIssue(field="section_count", expected=">=5", actual="3")
        ]
        mock_outline = MagicMock()
        mock_outline.title = "Retried Title"
        mock_outline.sections = [MagicMock()] * 5
        mock_outline.image_prompts = [MagicMock()]
        mock_outline.model_dump_json.return_value = '{"title":"Retried Title"}'
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

        from application.stage_runner import run_stage_compose

        run_stage_compose(
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

        marked = _mark_compliance_violations(content_md, report)

        assert marked.startswith("> ⚠️ **의료법 검증 미통과")
        assert "[first_person_promotion]" in marked
        assert "**⚠️ 특정 위반 문구 여기있음 ⚠️**" in marked

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

        marked = _mark_compliance_violations(content_md, report)

        assert "[patient_testimonial]" in marked
        assert "**⚠️" not in marked.split("---")[1]
