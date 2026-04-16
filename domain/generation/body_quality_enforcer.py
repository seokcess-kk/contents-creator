"""본문 품질 검증 + 부분 재생성 지원.

전체 재생성이 아닌 약한 섹션만 식별하여 보강 프롬프트를 생성한다.
LLM 호출은 이 파일에서 하지 않는다 (도메인 순수성 유지).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.generation.model import BodySection


@dataclass
class SectionIssue:
    """본문 섹션 품질 이슈 1건."""

    index: int
    subtitle: str
    issue: str  # "too_short" | "no_keyword" | "keyword_stuffing"
    detail: str


def find_weak_sections(
    body_sections: list[BodySection],
    keyword: str,
    target_total_chars: float,
) -> list[SectionIssue]:
    """약한 섹션을 찾아 구체적 이슈를 반환."""
    issues: list[SectionIssue] = []
    if not body_sections:
        return issues

    min_chars = _calc_min_section_chars(len(body_sections), target_total_chars)
    for section in body_sections:
        issues.extend(_check_section(section, keyword, min_chars))
    return issues


def _calc_min_section_chars(
    section_count: int,
    target_total_chars: float,
) -> float:
    """섹션당 최소 글자수 계산. 목표 총 글자수의 80%를 섹션에 배분."""
    target_per_section = target_total_chars / (section_count + 1)
    return max(target_per_section * 0.8, 300)


def _check_section(
    section: BodySection,
    keyword: str,
    min_chars: float,
) -> list[SectionIssue]:
    """단일 섹션의 글자수, 키워드 포함 여부를 검사."""
    issues: list[SectionIssue] = []
    content = section.content_md
    char_count = len(content)

    if char_count < min_chars:
        issues.append(
            SectionIssue(
                index=section.index,
                subtitle=section.subtitle,
                issue="too_short",
                detail=f"{char_count}자 (최소 {min_chars:.0f}자 필요)",
            )
        )

    kw_count = _count_keyword(content, keyword)
    if kw_count == 0:
        issues.append(
            SectionIssue(
                index=section.index,
                subtitle=section.subtitle,
                issue="no_keyword",
                detail=f"키워드 '{keyword}' 미포함",
            )
        )
    elif kw_count >= 4:
        issues.append(
            SectionIssue(
                index=section.index,
                subtitle=section.subtitle,
                issue="keyword_stuffing",
                detail=f"키워드 {kw_count}회 (3회 이하 권장)",
            )
        )

    return issues


def _count_keyword(content: str, keyword: str) -> int:
    """키워드 등장 횟수. 공백 무시 매칭도 시도."""
    count = content.count(keyword)
    if " " in keyword:
        normalized = keyword.replace(" ", "")
        count = max(count, content.replace(" ", "").count(normalized))
    return count


def build_section_fix_prompt(
    section_index: int,
    section_subtitle: str,
    section_content: str,
    issues: list[SectionIssue],
    keyword: str,
    intro_tone_hint: str,
) -> str:
    """약한 섹션의 보강 프롬프트를 생성한다."""
    descriptions = _build_issue_descriptions(section_index, issues, keyword)
    feedback = "\n".join(descriptions)

    return (
        f"아래 섹션을 보강해주세요. "
        f"톤과 문체는 유지하되, 다음 문제를 해결해주세요:\n\n"
        f"[문제점]\n{feedback}\n\n"
        f"[톤 힌트] {intro_tone_hint}\n\n"
        f"[현재 본문]\n## {section_subtitle}\n\n"
        f"{section_content}\n\n"
        f"위 내용을 보강하여 수정된 본문만 출력하세요. "
        f"소제목은 그대로 유지하세요."
    )


def _build_issue_descriptions(
    section_index: int,
    issues: list[SectionIssue],
    keyword: str,
) -> list[str]:
    """섹션 이슈를 사람이 읽을 수 있는 설명으로 변환."""
    descriptions: list[str] = []
    for issue in issues:
        if issue.index != section_index:
            continue
        if issue.issue == "too_short":
            descriptions.append(f"- 글자수가 부족합니다. {issue.detail}. 내용을 보강해주세요.")
        elif issue.issue == "no_keyword":
            descriptions.append(
                f"- '{keyword}' 키워드가 포함되어 있지 않습니다. 자연스럽게 1~2회 포함해주세요."
            )
        elif issue.issue == "keyword_stuffing":
            descriptions.append(
                f"- 키워드가 과도합니다. {issue.detail}. 일부를 자연스러운 표현으로 대체해주세요."
            )
    return descriptions
