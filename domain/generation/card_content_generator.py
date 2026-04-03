"""LLM 일괄 카드 콘텐츠 생성.

단일 LLM 호출로 3종 브랜디드 카드(intro, transition, cta) 텍스트를 생성한다.
pain/cause/solution/trust 내용은 SEO 텍스트에 흡수되었으므로 카드로 생성하지 않는다.
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
당신은 네이버 블로그용 브랜디드 이미지 카드의 카피를 작성하는 전문 카피라이터입니다.

규칙:
- 각 카드는 블로그 글 흐름 속에 삽입되는 브랜디드 이미지입니다
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
    """카드 콘텐츠 생성 프롬프트를 구성한다."""
    services_text = ", ".join(s.name for s in profile.services[:5])
    reviews_text = ""
    if profile.reviews:
        reviews_text = "\n".join(f'- "{r.text}" ({r.source})' for r in profile.reviews[:3])

    return f"""\
아래 정보를 바탕으로 브랜디드 카드 콘텐츠를 JSON 배열로 생성하세요.

## 생성할 카드 (순서대로)
{json.dumps(card_types, ensure_ascii=False)}

## 카드 타입별 역할
- intro: 업체 소개 + 공감 질문. hook과 brand_intro를 합친 카드. \
업체명을 포함하고, 독자의 공감을 끌어내는 질문이나 문장으로 시작
- transition: 고민에서 솔루션으로의 전환. 짧은 브릿지 카피
- cta: 마지막 후킹 + 연락처 정보. 행동 유도

## 키워드
{keyword}

## 업체 정보
- 업체명: {profile.company_name}
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
    """LLM으로 카드 콘텐츠를 일괄 생성한다.

    disclaimer는 제외하고 전달받은 card_types에 대해서만 생성.

    Returns:
        CardContent 리스트 (card_types 순서대로)
    """
    # disclaimer 제외
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
    """LLM 실패 시 최소한의 폴백 콘텐츠를 반환한다."""
    logger.warning("폴백 카드 콘텐츠 사용")
    results: list[CardContent] = []
    company = profile.company_name or keyword
    for ct in card_types:
        if ct == "intro":
            results.append(
                CardContent(
                    card_type=ct,
                    title=company,
                    subtitle=profile.usp or f"{profile.region} {profile.sub_category}",
                    body_text=f"{keyword} 관련 고민, 함께 알아보겠습니다.",
                )
            )
        elif ct == "transition":
            results.append(
                CardContent(
                    card_type=ct,
                    title="이제 달라질 수 있습니다",
                    body_text=f"{company}에서 준비한 솔루션을 확인해 보세요.",
                )
            )
        elif ct == "cta":
            results.append(
                CardContent(
                    card_type=ct,
                    title="지금 바로 상담받아 보세요",
                    body_text=f"{company} | {profile.phone or profile.region}",
                )
            )
        else:
            results.append(CardContent(card_type=ct, title=keyword))
    return results
