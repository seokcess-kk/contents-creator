"""L2 카피/메시지 분석. Claude API 기반.

제목 패턴, 도입부 훅, 톤앤매너, 설득 구조, 키워드를 분석한다.
"""

from __future__ import annotations

import json
import logging

from domain.analysis.model import HookPattern, L2Analysis, TitlePattern
from domain.common import llm_client

logger = logging.getLogger(__name__)

L2_SYSTEM = """\
당신은 네이버 블로그 SEO 콘텐츠 분석 전문가입니다.
블로그 포스트의 카피 패턴을 정확하게 분류합니다.
반드시 JSON만 반환하세요.
"""

L2_PROMPT = """\
아래 블로그 포스트를 분석하세요.

[제목] {title}

[본문]
{text}

다음 JSON 형태로 반환하세요:
{{
  "title_type": "질문형/숫자형/감정형/방법론형/리스트형 중 하나",
  "hook_type": "공감형/통계형/질문형/스토리형/시즌형 중 하나",
  "tone": "전문가형/친근형/스토리텔링형/정보전달형 중 하나",
  "persuasion": "AIDA/PAS/문제-원인-솔루션/비포-애프터 중 하나",
  "keyword_placement": {{
    "title": ["키워드1"],
    "first_paragraph": ["키워드2"],
    "subtitles": ["키워드3"],
    "last_paragraph": ["키워드4"]
  }},
  "related_keywords": ["연관키워드1", "연관키워드2"],
  "lsi_keywords": ["LSI키워드1", "LSI키워드2"]
}}
"""


def analyze_copy_single(title: str, text: str) -> dict:
    """단일 포스트의 카피를 분석한다.

    Args:
        title: 포스트 제목
        text: 포스트 본문 텍스트

    Returns:
        분석 결과 dict
    """
    prompt = L2_PROMPT.format(title=title, text=text[:4000])

    try:
        response = llm_client.chat_json(prompt, system=L2_SYSTEM, max_tokens=1024)
        return json.loads(response)
    except Exception as e:
        logger.error("L2 분석 실패: %s", e)
        return {}


def aggregate_l2(results: list[dict]) -> L2Analysis:
    """N개 포스트의 L2 분석 결과를 집계한다."""
    if not results:
        return L2Analysis()

    # 제목 패턴 집계
    title_counter: dict[str, list[str]] = {}
    hook_counter: dict[str, list[str]] = {}
    tone_counter: dict[str, int] = {}
    persuasion_list: list[str] = []
    all_related: list[str] = []
    all_lsi: list[str] = []

    for r in results:
        if not r:
            continue

        # 제목
        tt = r.get("title_type", "")
        if tt:
            title_counter.setdefault(tt, [])

        # 훅
        ht = r.get("hook_type", "")
        if ht:
            hook_counter.setdefault(ht, [])

        # 톤
        tone = r.get("tone", "")
        if tone:
            tone_counter[tone] = tone_counter.get(tone, 0) + 1

        # 설득 구조
        ps = r.get("persuasion", "")
        if ps:
            persuasion_list.append(ps)

        # 키워드
        all_related.extend(r.get("related_keywords", []))
        all_lsi.extend(r.get("lsi_keywords", []))

    n = len(results)

    # TitlePattern 생성
    title_patterns = [
        TitlePattern(
            type=t,
            count=len(examples),
            examples=examples[:3],
            weight=round(len(examples) / n, 2) if n > 0 else 0,
        )
        for t, examples in title_counter.items()
    ]
    # count가 0인 경우 results 수로 보정
    for tp in title_patterns:
        if tp.count == 0:
            tp.count = sum(1 for r in results if r.get("title_type") == tp.type)
            tp.weight = round(tp.count / n, 2) if n > 0 else 0

    # HookPattern 생성
    hook_patterns = [
        HookPattern(type=h, count=sum(1 for r in results if r.get("hook_type") == h))
        for h in hook_counter
    ]

    # 연관 키워드 중복 제거 + 빈도순
    related_freq: dict[str, int] = {}
    for kw in all_related:
        related_freq[kw] = related_freq.get(kw, 0) + 1
    sorted_related = sorted(related_freq, key=related_freq.get, reverse=True)[:10]  # type: ignore[arg-type]

    lsi_freq: dict[str, int] = {}
    for kw in all_lsi:
        lsi_freq[kw] = lsi_freq.get(kw, 0) + 1
    sorted_lsi = sorted(lsi_freq, key=lsi_freq.get, reverse=True)[:10]  # type: ignore[arg-type]

    return L2Analysis(
        title_patterns=title_patterns,
        hook_patterns=hook_patterns,
        tone_distribution=tone_counter,
        persuasion_structures=list(set(persuasion_list)),
        related_keywords=sorted_related,
        lsi_keywords=sorted_lsi,
    )
