"""SEO 텍스트 생성기. Claude API로 블로그 원고를 생성한다.

패턴 카드(뼈대) + 클라이언트 프로필 + 변이 조합 → SEO 최적화 텍스트.
의료 업종이면 1차 방어(의료법 규칙 프롬프트 주입)를 적용한다.
"""

from __future__ import annotations

import logging

from domain.analysis.model import PatternCard
from domain.common import llm_client
from domain.compliance.rules import DISCLAIMER_TEMPLATE
from domain.generation.expression_filter import filter_expressions
from domain.generation.model import VariationConfig
from domain.generation.structure_templates import get_template
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)

SEO_SYSTEM = """\
당신은 네이버 블로그 SEO 콘텐츠 전문 작가입니다.
패턴 카드의 구조적 제약(뼈대)을 준수하면서, 클라이언트의 브랜드 톤에 맞는 자연스러운 글을 작성합니다.
네이버 블로그 최적화: 제목 30자 내외, 키워드 자연 배치, 가독성 높은 문단 구성.
AI 상투 표현("~하는 것이 중요합니다", "~에 대해 알아보겠습니다")을 절대 사용하지 마세요.
"""

MEDICAL_COMPLIANCE_INJECTION = """\

[의료광고법 준수 규칙 — 반드시 지킬 것]
의료법 제56조에 의해 아래 표현을 절대 사용하지 마세요:

[CRITICAL — 사용 시 즉시 위반]
- 치료 보장: "100% 완치", "확실한 효과", "반드시 좋아집니다"
- 최상급 비교: "최고의", "유일한", "국내 1위", "독보적인"
- 절대적 보장: "무조건", "부작용 없는", "통증 제로"
- 만족도 언급: "많은 분들이 만족", "높은 만족도", "만족스러운 결과"
- 결과 단정: "~될 것입니다", "~효과를 보실 수 있습니다"
- 근본적/완벽: "근본적인 해결", "완벽한 솔루션", "정확히 분석"

[WARNING — 주의 필요]
- 체험기 형식: 치료 과정이나 변화를 시간순 서술 금지 ("시작한 후", "시간이 지나면서", "점차 변화가")
- 경험 일반화: "많은 분들이 ~", "~를 경험하고 계십니다", "~변화를 경험", "~를 느끼는 경우"
- 과대 수식어: "최적의", "성공적인", "놀라운 변화", "특별한"
- 비교 우위: "~중에서도 ~이 특별한 이유", "다른 곳과 달리"
- 전후 비교 묘사: 치료 전후 변화를 구체적으로 묘사하는 표현

[안전한 대체 표현]
- "개인차가 있을 수 있습니다"
- "풍부한 임상 경험을 바탕으로"
- "도움이 될 수 있습니다" ("될 것입니다" 대신)
- "적합한" ("최적의" 대신)
- "개선에 도움을 줄 수 있습니다" ("근본적 해결" 대신)

글 마지막에 아래 Disclaimer를 반드시 포함하세요:
{disclaimer}
"""

SEO_PROMPT = """\
아래 조건에 맞는 네이버 블로그 SEO 원고를 작성하세요.
이 원고는 브랜드 이미지 섹션 아래에 배치되는 정보성 블로그 글입니다.
상위 노출을 위한 키워드 최적화에 집중하세요.
pain/고민, cause/원인, solution/솔루션, trust/신뢰 내용을 모두 텍스트 안에 포함하세요.

## 키워드: {keyword}

## 구조 (이 순서대로 작성)
{section_order}

## 패턴 카드 제약 (뼈대)
- 글자수: {char_min}~{char_max}자
- 소제목 수: {sub_min}~{sub_max}개
- 필수 키워드: {required_keywords}
- 연관 키워드 (자연스럽게 분산 배치): {related_keywords}

## 도입부 스타일: {intro_style}
## 소제목 스타일: {subtitle_style}

## 클라이언트 정보
- 업체명: {company_name}
- 서비스: {services}
- USP: {usp}
- 톤앤매너: {tone}
{prohibited_note}

## 이미지 배치 표시
이미지가 들어갈 위치에 [이미지: 설명] 형태로 표시하세요.
배치 패턴: {image_placement}

## 섹션 배경색 디렉티브 (필수)
각 섹션의 분위기에 맞는 배경색을 지정하세요. 섹션 시작 줄 바로 위에 작성합니다.
- `<!-- SECTION:도입 bg=#f5f0eb -->` — 따뜻한 배경 (도입부)
- `<!-- SECTION:고민 bg=#ffffff -->` — 흰 배경 (고민/문제)
- `<!-- SECTION:솔루션 bg=#f0f4f8 -->` — 시원한 배경 (해결책)
- `<!-- SECTION:신뢰 bg=#f5f0eb -->` — 따뜻한 배경 (후기/신뢰)
색상은 글의 톤에 맞게 자유롭게 조정 가능합니다. 3-5개 섹션에 배경색을 지정하세요.

## 리치 스타일 지시
- 고객 고민이나 후기 인용 시 인용문(`> `) 형식을 적극 사용하세요
- 핵심 키워드나 중요 표현은 `**볼드**`로 강조하세요 (형광펜 효과로 렌더링됩니다)
- 각 섹션이 시각적으로 구분되도록 작성하세요

## 출력 형식
마크다운으로 작성하세요.
- 제목은 # 으로
- 소제목은 ## 으로
- 본문은 일반 텍스트로
- 인용문은 > 으로
- 나열 항목은 반드시 `- ` (하이픈+공백) 형식 리스트로 작성 (번호 리스트 금지)

## 섹션 배치 규칙 (중요)
- SECTION 디렉티브는 해당 섹션의 **첫 줄 바로 위**에 작성하세요
- 소제목(##)은 반드시 SECTION 디렉티브 **아래**에 배치하세요 (위에 두지 마세요)
- 올바른 순서: SECTION 디렉티브 → 소제목 → 본문 → 다음 SECTION 디렉티브
"""


def generate_seo_text(
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
    variation: VariationConfig,
) -> tuple[str, str]:
    """SEO 블로그 원고를 생성한다.

    Args:
        keyword: 타겟 키워드
        pattern_card: 분석 패턴 카드
        profile: 클라이언트 프로필
        variation: 변이 조합

    Returns:
        (제목, 본문 마크다운) 튜플
    """
    # 시스템 프롬프트 구성
    system = SEO_SYSTEM

    # 의료법 1차 방어: 의료 업종이면 규칙 주입
    if profile.is_medical():
        logger.info("의료법 1차 방어 적용: 프롬프트에 규칙 주입")
        system += MEDICAL_COMPLIANCE_INJECTION.format(disclaimer=DISCLAIMER_TEMPLATE)

    # 구조 템플릿
    template = get_template(variation.structure)
    section_order = (
        "\n".join(f"{i}. {s}" for i, s in enumerate(template.sections, 1))
        if template
        else "1. 도입\n2. 본론\n3. 결론\n4. CTA"
    )

    # 패턴 카드에서 제약 추출
    tp = pattern_card.text_pattern
    char_range = tp.get("char_range", [1500, 3500])
    sub_range = tp.get("subtitle_count", [3, 6])
    required_kw = ", ".join(tp.get("required_keywords", [keyword]))
    related_kw = ", ".join(tp.get("related_keywords", [])[:8])

    # 프로필 정보
    services_str = ", ".join(s.name for s in profile.services[:5]) or "미설정"
    prohibited_note = ""
    if profile.prohibited_expressions:
        prohibited_note = (
            f"\n## 금지 표현 (절대 사용 금지)\n{', '.join(profile.prohibited_expressions)}"
        )

    prompt = SEO_PROMPT.format(
        keyword=keyword,
        section_order=section_order,
        char_min=char_range[0],
        char_max=char_range[1],
        sub_min=sub_range[0],
        sub_max=sub_range[1],
        required_keywords=required_kw,
        related_keywords=related_kw,
        intro_style=variation.intro,
        subtitle_style=variation.subtitle_style,
        company_name=profile.company_name or "미설정",
        services=services_str,
        usp=profile.usp or "미설정",
        tone=profile.tone_and_manner or "전문가형",
        prohibited_note=prohibited_note,
        image_placement=variation.image_placement,
    )

    # LLM 호출
    raw_text = llm_client.chat(
        prompt,
        system=system,
        max_tokens=4096,
        temperature=0.7,
    )

    # ④ 문장 표현 변이: AI 상투 표현 필터링
    filtered_text, detected = filter_expressions(raw_text)
    if detected:
        logger.info("AI 상투 표현 %d개 감지·대체: %s", len(detected), detected[:3])

    # 제목 추출
    title = _extract_title(filtered_text)

    return title, filtered_text


def _extract_title(text: str) -> str:
    """마크다운에서 제목(# )을 추출한다."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return ""
