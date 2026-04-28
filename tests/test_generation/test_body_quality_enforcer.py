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


class TestEdgeCases:
    """추가 엣지 케이스 — 경계값/혼합 이슈/빈 콘텐츠."""

    def test_multiple_weak_sections_returns_per_section_issues(self) -> None:
        """여러 섹션이 동시에 약하면 각 섹션별로 이슈 누적."""
        sections = [
            _make_section(index=2, subtitle="A", content="짧음"),
            _make_section(index=3, subtitle="B", content="가" * 100),  # short + no kw
        ]
        issues = find_weak_sections(sections, "다이어트", 2800)
        # 두 섹션 모두 too_short 발생
        too_short_indices = {i.index for i in issues if i.issue == "too_short"}
        assert too_short_indices == {2, 3}
        # 두 섹션 모두 no_keyword 발생 ("다이어트" 미포함)
        no_kw_indices = {i.index for i in issues if i.issue == "no_keyword"}
        assert no_kw_indices == {2, 3}

    def test_keyword_count_three_is_not_stuffing(self) -> None:
        """경계값: kw_count == 3 은 stuffing 아님 (코드: >= 4)."""
        kw = "다이어트"
        content = (kw + " 본문. ") * 3 + "가" * 1000
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, kw, 2800)
        assert "keyword_stuffing" not in [i.issue for i in issues]

    def test_keyword_count_four_is_stuffing(self) -> None:
        """경계값: kw_count == 4 부터 stuffing."""
        kw = "다이어트"
        content = (kw + " 본문. ") * 4 + "가" * 1000
        sections = [_make_section(content=content)]
        issues = find_weak_sections(sections, kw, 2800)
        assert "keyword_stuffing" in [i.issue for i in issues]

    def test_mixed_issues_in_single_section(self) -> None:
        """too_short + no_keyword 동시 발생 가능."""
        sections = [_make_section(content="짧음")]  # 짧고 키워드 없음
        issues = find_weak_sections(sections, "다이어트한의원", 2800)
        types = {i.issue for i in issues}
        assert "too_short" in types
        assert "no_keyword" in types

    def test_empty_content_section(self) -> None:
        sections = [_make_section(content="")]
        issues = find_weak_sections(sections, "키워드", 2800)
        assert any(i.issue == "too_short" for i in issues)
        assert any(i.issue == "no_keyword" for i in issues)


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

    def test_includes_keyword_stuffing_description(self) -> None:
        """keyword_stuffing 분기 문구가 프롬프트에 정확히 포함."""
        from domain.generation.body_quality_enforcer import SectionIssue

        issues = [
            SectionIssue(
                index=2,
                subtitle="소제목",
                issue="keyword_stuffing",
                detail="키워드 5회 (3회 이하 권장)",
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
        assert "키워드가 과도" in prompt
        assert "자연스러운 표현으로 대체" in prompt
