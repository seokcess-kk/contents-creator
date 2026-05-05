"""SPEC-BATCH §12 Phase 5+ PR1 — 본문 차별화 검증 (Jaccard).

cluster_dedupe ON 정책의 1페이지 노출 리스크 mitigation. cluster member 가
primary 의 PatternCard 를 재사용해 본문을 생성한 뒤, primary 본문과 단어 단위
Jaccard 유사도를 측정한다. 임계값 초과 시 batch_orchestrator 가 needs_review
강제 마킹.

설계:
- 단어 n-gram (default n=3) 단위 Jaccard — 의미 유사 + 구조 유사 양쪽 포착
- 한글 특화 토크나이저 X — `re.findall(r"\\w+")` 단순 분할 (한글 자모 포함).
  외부 형태소 분석기 없이도 1페이지 노출 리스크는 충분히 잡힌다 (실측은 Phase 5
  PR2 negative example 도입 후 재검토)
- generated_contents.content_md 컬럼에서 본문 fetch — Supabase 미설정/실패/부재
  graceful (None 반환)

호출 위치:
- `application.batch_orchestrator._dispatch_item` 의 cluster reuse + generate/pipeline
  분기 직후
"""

from __future__ import annotations

import logging
import re
from typing import Any, cast

from config.supabase import get_client

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def jaccard_similarity(text_a: str, text_b: str, *, ngram: int = 3) -> float:
    """두 텍스트의 단어 n-gram Jaccard 유사도.

    범위: [0.0, 1.0]. 둘 다 빈 토큰이면 1.0 (완전 일치 — 폴백). 한쪽만 빈 토큰이면
    0.0. n-gram 길이보다 짧으면 단어 단위로 fallback (n=1).

    실측: ngram=3 + 임계값 0.7 가 1페이지 노출 리스크 합리적 차단점 (lessons 참조).
    """
    tokens_a = _WORD_RE.findall(text_a or "")
    tokens_b = _WORD_RE.findall(text_b or "")
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    shingles_a = _shingles(tokens_a, ngram)
    shingles_b = _shingles(tokens_b, ngram)
    if not shingles_a or not shingles_b:
        return 0.0

    intersection = shingles_a & shingles_b
    union = shingles_a | shingles_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _shingles(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    """단어 n-gram set. n 이 토큰 수보다 크면 단일 token shingles 로 폴백."""
    if n <= 1 or len(tokens) < n:
        return {(t,) for t in tokens}
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def fetch_content_md(generated_content_id: str | None) -> str | None:
    """`generated_contents.content_md` 컬럼 fetch. 실패/부재 시 None (graceful).

    cluster member 본문 차별화 검증 시 primary / member 본문을 가져오는 단일 출처.
    Supabase 미설정 / row 부재 / 컬럼 부재 모두 graceful 처리. 검증 호출자는
    None 을 받으면 검증 스킵 (logger.warning).
    """
    if generated_content_id is None:
        return None
    try:
        result = (
            get_client()
            .table("generated_contents")
            .select("content_md")
            .eq("id", generated_content_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "text_similarity.fetch_failed gen_id=%s", generated_content_id, exc_info=True
        )
        return None
    rows = result.data or []
    if not rows:
        return None
    raw = cast("dict[str, Any]", rows[0]).get("content_md")
    if not isinstance(raw, str):
        return None
    return raw


__all__ = ["jaccard_similarity", "fetch_content_md"]
