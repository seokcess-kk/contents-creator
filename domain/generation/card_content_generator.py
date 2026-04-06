"""LLM 일괄 카드 콘텐츠 생성.

5종 브랜드 카드(greeting, empathy, service, trust, cta) 텍스트를 생성한다.
disclaimer는 고정 템플릿이므로 LLM에 요청하지 않는다.
"""

from __future__ import annotations

import json
import logging

from domain.analysis.model import PatternCard
from domain.common import llm_client
from domain.generation.model import CardContent
from domain.profile.model import ClientProfile

logger = logging.getLogger(__name__)

CARD_CONTENT_SYSTEM = """\
당신은 네이버 블로그용 브랜드 이미지 카드의 카피를 작성하는 전문 카피라이터입니다.

규칙:
- 각 카드는 블로그 글 상단에 연속 배치되는 브랜드 이미지입니다
- title: 1줄, 최대 25자
- subtitle: 1줄, 최대 35자 (없으면 빈 문자열)
- body_text: 1-3줄, 최대 100자
- items: 리스트형 항목, 각 항목 최대 30자
- badge_text: 통계 뱃지나 라벨, 최대 15자 (없으면 빈 문자열)
- 자연스러운 한국어, AI 상투 표현 금지
- 반드시 JSON 배열만 반환하세요
"""

MEDICAL_CARD_INJECTION = """
의료광고법 준수 (CRITICAL):
- "100% 완치", "확실한 효과", "최고의" 등 과대/비교/보장 표현 절대 금지
- 안전한 표현: "도움이 될 수 있습니다", "개인차가 있을 수 있습니다"
- 시술 전후 비교, 결과 보장 문구 금지
"""


def _build_card_prompt(
    card_types: list[str],
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> str:
    """5종 브랜드 카드 콘텐츠 생성 프롬프트."""
    services_text = ", ".join(s.name for s in profile.services[:5])
    reviews_text = ""
    if profile.reviews:
        reviews_text = "\n".join(f'- "{r.text}" ({r.source})' for r in profile.reviews[:3])

    return f"""\
아래 정보를 바탕으로 브랜드 이미지 카드 콘텐츠를 JSON 배열로 생성하세요.
이 카드들은 블로그 글 상단에 연속 배치되어 브랜드를 소개하는 이미지 섹션입니다.

## 생성할 카드 (순서대로)
{json.dumps(card_types, ensure_ascii=False)}

## 카드 타입별 역할
- greeting: 원장/대표 인사말. 따뜻한 첫인상, 업체명 포함, 공감 유도
- empathy: 타겟 고객 고민 공감. "이런 고민 있으신가요?" 스타일 후킹
- service: 핵심 서비스 3~4개 소개. items 필드에 서비스명 나열, USP 강조
- trust: 실적 수치나 후기 인용. badge_text에 핵심 수치, 신뢰 구축
- cta: 마지막 후킹 + 연락처. 행동 유도 메시지 (버튼 없이 텍스트로)

## 키워드
{keyword}

## 업체 정보
- 업체명: {profile.company_name}
- 대표/원장: {profile.representative or "(미입력)"}
- 업종: {profile.industry} > {profile.sub_category}
- 지역: {profile.region}
- 서비스: {services_text}
- USP: {profile.usp}
- 톤앤매너: {profile.tone_and_manner or "자연스러운"}
- 전화번호: {profile.phone or "(없음)"}
- 주소: {profile.address or "(없음)"}

## 후기
{reviews_text or "(없음)"}

## 출력 형식
JSON 배열, 각 요소는 다음 키를 포함:
card_type, title, subtitle, body_text, items(배열), badge_text
"""


def generate_card_contents(
    card_types: list[str],
    keyword: str,
    pattern_card: PatternCard,
    profile: ClientProfile,
) -> list[CardContent]:
    """LLM으로 브랜드 카드 콘텐츠를 일괄 생성한다."""
    llm_types = [t for t in card_types if t != "disclaimer"]
    if not llm_types:
        return []

    system = CARD_CONTENT_SYSTEM
    if profile.is_medical():
        system += MEDICAL_CARD_INJECTION

    prompt = _build_card_prompt(llm_types, keyword, pattern_card, profile)

    logger.info("카드 콘텐츠 생성 중 (%d장)...", len(llm_types))
    raw = llm_client.chat_json(prompt, system=system, max_tokens=4096)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("카드 콘텐츠 JSON 파싱 실패")
        return _fallback_contents(llm_types, keyword, profile)

    if not isinstance(data, list):
        logger.error("카드 콘텐츠 응답이 배열이 아님")
        return _fallback_contents(llm_types, keyword, profile)

    contents: list[CardContent] = []
    for i, card_type in enumerate(llm_types):
        if i < len(data):
            item = data[i]
            contents.append(
                CardContent(
                    card_type=card_type,
                    title=item.get("title", ""),
                    subtitle=item.get("subtitle", ""),
                    body_text=item.get("body_text", ""),
                    items=item.get("items", []),
                    badge_text=item.get("badge_text", ""),
                )
            )
        else:
            contents.append(CardContent(card_type=card_type))

    logger.info("카드 콘텐츠 생성 완료: %d장", len(contents))
    return contents


def _fallback_contents(
    card_types: list[str],
    keyword: str,
    profile: ClientProfile,
) -> list[CardContent]:
    """LLM 실패 시 최소한의 폴백 콘텐츠."""
    logger.warning("폴백 카드 콘텐츠 사용")
    company = profile.company_name or keyword
    fallbacks: dict[str, CardContent] = {
        "greeting": CardContent(
            card_type="greeting",
            title=company,
            subtitle=profile.usp or f"{profile.region} {profile.sub_category}",
            body_text=f"{keyword} 관련 고민, 함께 알아보겠습니다.",
        ),
        "empathy": CardContent(
            card_type="empathy",
            title="이런 고민 있으신가요?",
            body_text=f"{keyword} 때문에 걱정되시나요?",
        ),
        "service": CardContent(
            card_type="service",
            title="서비스 안내",
            items=[s.name for s in profile.services[:4]],
        ),
        "trust": CardContent(
            card_type="trust",
            title="신뢰할 수 있는 이유",
            body_text=f"{company}의 전문적인 관리를 받아보세요.",
        ),
        "cta": CardContent(
            card_type="cta",
            title="지금 바로 상담받아 보세요",
            body_text=f"{company} | {profile.phone or profile.region}",
        ),
    }
    return [fallbacks.get(ct, CardContent(card_type=ct)) for ct in card_types]
