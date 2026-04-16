"""body_quality_enforcer.py 단위 테스트."""

from __future__ import annotations

from domain.generation.body_quality_enforcer import (
    build_section_fix_prompt,
    find_weak_sections,
)
from domain.generation.model import BodySection


def _make_section(
    index: int = 2,
    subtitle: str = "소제목",
    content: str = "다이어트 한의원에 대한 본문 내용입니다.",
) -> BodySection:
    return BodySection(index=index, subtitle=subtitle, content_md=content)


class TestFindWeakSections:
    def test_no_issues_when_all_ok(self) -> None:
        # keyword 2회 + 충분한 글자수
        content = (
            "다이어트 한의원에 대한 정보를 정리했습니다. "
            + "건강한 생활 습관을 유지하는 것이 중요합니다. " * 50
            + "다이어트 한의원을 방문하기 전에 알아야 할 점이 있습니다."
        )
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, "다이어트 한의원", 2800)
        assert issues == []

    def test_detects_too_short(self) -> None:
        sections = [_make_section(content="짧은 내용")]
        issues = find_weak_sections(sections, "다이어트", 2800)
        issue_types = [i.issue for i in issues]
        assert "too_short" in issue_types

    def test_detects_no_keyword(self) -> None:
        sections = [
            _make_section(content="가" * 800),  # long enough, no keyword
        ]
        issues = find_weak_sections(sections, "다이어트 한의원", 2800)
        issue_types = [i.issue for i in issues]
        assert "no_keyword" in issue_types

    def test_detects_keyword_stuffing(self) -> None:
        kw = "다이어트"
        content = (kw + " 관련 내용. ") * 5  # 5 occurrences
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, kw, 100)
        issue_types = [i.issue for i in issues]
        assert "keyword_stuffing" in issue_types

    def test_empty_sections(self) -> None:
        issues = find_weak_sections([], "키워드", 2800)
        assert issues == []

    def test_space_normalized_keyword_match(self) -> None:
        """공백 무시 매칭 (예: '다이어트한의원' == '다이어트 한의원')."""
        content = "다이어트한의원에 대한 정보입니다. " * 20
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, "다이어트 한의원", 2800)
        issue_types = [i.issue for i in issues]
        assert "no_keyword" not in issue_types

    def test_min_chars_at_least_200(self) -> None:
        """target_total_chars가 작아도 최소 200자 기준 유지."""
        content = "가" * 199
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, "가", 100)
        issue_types = [i.issue for i in issues]
        assert "too_short" in issue_types


class TestBuildSectionFixPrompt:
    def test_includes_issue_descriptions(self) -> None:
        from domain.generation.body_quality_enforcer import SectionIssue

        issues = [
            SectionIssue(
                index=2,
                subtitle="소제목",
                issue="too_short",
                detail="100자 (최소 300자 필요)",
            ),
            SectionIssue(
                index=2,
                subtitle="소제목",
                issue="no_keyword",
                detail="키워드 '다이어트' 미포함",
            ),
        ]
        prompt = build_section_fix_prompt(
            section_index=2,
            section_subtitle="소제목",
            section_content="짧은 내용",
            issues=issues,
            keyword="다이어트",
            intro_tone_hint="공감형 톤",
        )
        assert "글자수가 부족" in prompt
        assert "키워드가 포함되어 있지 않" in prompt
        assert "공감형 톤" in prompt

    def test_ignores_other_section_issues(self) -> None:
        from domain.generation.body_quality_enforcer import SectionIssue

        issues = [
            SectionIssue(
                index=3,
                subtitle="다른 소제목",
                issue="too_short",
                detail="50자",
            ),
        ]
        prompt = build_section_fix_prompt(
            section_index=2,
            section_subtitle="소제목",
            section_content="내용",
            issues=issues,
            keyword="다이어트",
            intro_tone_hint="톤",
        )
        assert "글자수가 부족" not in prompt
