"""클라이언트 프로필 자동 추출.

홈페이지/블로그 URL에서 업체 정보를 80% 자동 추출한다.
금지 표현은 추출 불가 → 수동 입력 안내.
"""

from __future__ import annotations

import json
import logging

from domain.common import llm_client
from domain.crawler.homepage_scraper import scrape_homepage
from domain.profile.model import ClientProfile, ServiceItem

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
당신은 웹페이지에서 비즈니스 정보를 추출하는 전문가입니다.
반드시 JSON만 반환하세요. 마크다운이나 설명은 포함하지 마세요.
"""

EXTRACTION_USER_PROMPT = """\
아래 웹페이지들의 내용을 분석하여 비즈니스 프로필을 추출하세요.

{pages_content}

다음 JSON 형태로 반환하세요:
{{
  "company_name": "정확한 상호명",
  "representative": "대표자/원장 이름 (없으면 빈 문자열)",
  "industry": "의료/뷰티/건강 중 하나",
  "sub_category": "세부 카테고리 (예: 피부과, 한의원, 치과)",
  "region": "시/구 단위 지역 (예: 서울 강남구)",
  "services": [
    {{"name": "서비스명", "description": "한 줄 설명"}}
  ],
  "tone_and_manner": "전문가형/친근형/스토리텔링형/정보전달형 중 하나",
  "usp": "이 업체의 핵심 차별점 한 줄",
  "frequent_expressions": ["자주 사용하는 표현1", "표현2"],
  "confidence": {{
    "company_name": "high/medium/low",
    "representative": "high/medium/low",
    "industry": "high/medium/low",
    "services": "high/medium/low",
    "tone_and_manner": "high/medium/low",
    "usp": "high/medium/low"
  }}
}}
"""


def extract_profile(url: str, max_pages: int = 10) -> ClientProfile:
    """URL에서 클라이언트 프로필을 자동 추출한다.

    Args:
        url: 홈페이지 또는 블로그 URL
        max_pages: 크롤링할 최대 페이지 수

    Returns:
        추출된 ClientProfile (status="draft")
    """
    # 1. 페이지 크롤링
    logger.info("프로필 추출 시작: %s", url)
    pages = scrape_homepage(url, max_pages=max_pages)
    successful_pages = [p for p in pages if p.success]

    if not successful_pages:
        logger.error("크롤링 성공한 페이지가 없습니다: %s", url)
        return ClientProfile(source_url=url, status="draft")

    # 2. LLM으로 프로필 추출
    pages_content = "\n\n---\n\n".join(
        f"[페이지: {p.url}]\n제목: {p.title}\n\n{p.text_content[:3000]}" for p in successful_pages
    )

    prompt = EXTRACTION_USER_PROMPT.format(pages_content=pages_content)

    try:
        response = llm_client.chat_json(
            prompt,
            system=EXTRACTION_SYSTEM_PROMPT,
            max_tokens=2048,
        )
        data = json.loads(response)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("프로필 추출 LLM 응답 파싱 실패: %s", e)
        return ClientProfile(source_url=url, status="draft")

    # 3. ClientProfile 구성
    services = [
        ServiceItem(name=s.get("name", ""), description=s.get("description", ""))
        for s in data.get("services", [])
    ]

    confidence = data.get("confidence", {})

    profile = ClientProfile(
        company_name=data.get("company_name", ""),
        representative=data.get("representative", ""),
        industry=data.get("industry", ""),
        sub_category=data.get("sub_category", ""),
        region=data.get("region", ""),
        services=services,
        tone_and_manner=data.get("tone_and_manner", ""),
        usp=data.get("usp", ""),
        frequent_expressions=data.get("frequent_expressions", []),
        source_url=url,
        status="draft",
        confidence_scores=confidence,
    )

    logger.info(
        "프로필 추출 완료: %s (%d페이지 분석)",
        profile.company_name or "(이름 미추출)",
        len(successful_pages),
    )
    return profile


def format_review_prompt(profile: ClientProfile) -> str:
    """사용자 리뷰용 프롬프트를 생성한다."""
    lines = [
        f"# 클라이언트 프로필 초안 — {profile.company_name or '(미추출)'}",
        "",
        "## 자동 추출 결과 (확인해 주세요)",
        "",
        "| 항목 | 추출 값 | 신뢰도 |",
        "|------|---------|--------|",
    ]

    fields = [
        ("업체명", profile.company_name, "company_name"),
        ("대표자/원장", profile.representative, "representative"),
        ("업종", f"{profile.industry} > {profile.sub_category}", "industry"),
        ("지역", profile.region, "region"),
        ("톤앤매너", profile.tone_and_manner, "tone_and_manner"),
        ("USP", profile.usp, "usp"),
    ]

    for label, value, key in fields:
        conf = profile.confidence_scores.get(key, "-")
        lines.append(f"| {label} | {value or '(미추출)'} | {conf} |")

    if profile.services:
        lines.append("")
        lines.append("### 주요 서비스")
        for s in profile.services:
            lines.append(f"- **{s.name}**: {s.description}")

    if profile.frequent_expressions:
        lines.append("")
        lines.append(f"### 자주 쓰는 표현: {', '.join(profile.frequent_expressions)}")

    lines.extend(
        [
            "",
            "## 수동 입력 필요",
            "- [ ] 금지 표현·키워드: ___",
            "- [ ] 타겟 고객 페르소나 (연령, 성별, 주요 고민): ___",
            "",
            "## 수정이 필요한 항목이 있으면 알려주세요",
        ]
    )

    return "\n".join(lines)
