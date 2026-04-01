"""구조 템플릿 풀. 5~10개 기본 템플릿 + 동적 학습."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StructureTemplate:
    """구조 변이 템플릿."""

    name: str
    sections: list[str]
    description: str


# 기본 템플릿 풀 (SPEC 기준 5~10개)
TEMPLATES: list[StructureTemplate] = [
    StructureTemplate(
        name="문제해결형",
        sections=["도입", "문제제기", "원인분석", "솔루션", "차별점", "사례", "CTA"],
        description="문제→원인→솔루션 흐름. 의료/건강 콘텐츠에 적합",
    ),
    StructureTemplate(
        name="스토리공감형",
        sections=["도입(스토리)", "공감", "정보제공", "솔루션", "비교", "CTA"],
        description="스토리로 시작하여 공감을 유도. 뷰티/라이프 콘텐츠에 적합",
    ),
    StructureTemplate(
        name="QA형",
        sections=["도입(질문)", "답변", "근거", "사례", "차별점", "CTA"],
        description="질문→답변 구조. SEO 검색 의도에 직접 대응",
    ),
    StructureTemplate(
        name="시즌연결형",
        sections=["도입(계절이슈)", "연결", "서비스소개", "효과", "후기", "CTA"],
        description="계절/시기 이슈에서 서비스로 자연스럽게 연결",
    ),
    StructureTemplate(
        name="데이터기반형",
        sections=["도입(통계)", "문제인식", "해결방법", "전문가팁", "CTA"],
        description="통계/데이터로 시작하여 권위감 부여",
    ),
    StructureTemplate(
        name="리스트형",
        sections=["도입", "항목1", "항목2", "항목3", "항목4", "항목5", "정리", "CTA"],
        description="N가지 방법/이유 나열. 스캔 가독성 높음",
    ),
    StructureTemplate(
        name="비포애프터형",
        sections=["도입", "비포(문제상황)", "전환점", "애프터(결과)", "방법", "CTA"],
        description="변화 전후를 대비하여 임팩트 극대화",
    ),
    StructureTemplate(
        name="전문가칼럼형",
        sections=["도입(전문지식)", "개념설명", "오해바로잡기", "올바른방법", "요약", "CTA"],
        description="전문성을 강조하는 칼럼 스타일",
    ),
]


def get_template(name: str) -> StructureTemplate | None:
    """이름으로 템플릿을 조회한다."""
    for t in TEMPLATES:
        if t.name == name:
            return t
    return None


def get_all_template_names() -> list[str]:
    """모든 템플릿 이름을 반환한다."""
    return [t.name for t in TEMPLATES]
