"""application/text_similarity — Jaccard + content_md fetch 단위 테스트."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from application import text_similarity

# ── jaccard_similarity ──


def test_jaccard_identical_text_returns_one() -> None:
    text = "다이어트 한의원 천안에서 살 빼는 법 효과적인 다이어트"
    assert text_similarity.jaccard_similarity(text, text, ngram=3) == 1.0


def test_jaccard_completely_different_returns_zero() -> None:
    a = "다이어트 한의원 천안 살빼기 방법"
    b = "비염 치료 강남 진료 상담"
    score = text_similarity.jaccard_similarity(a, b, ngram=3)
    assert score == 0.0


def test_jaccard_partial_overlap() -> None:
    """일부 n-gram 만 공유 — 0 < score < 1."""
    a = "다이어트 한의원 천안 추천 후기 효과 좋은 곳"
    b = "다이어트 한의원 천안 후기 좋은 곳 정리"
    score = text_similarity.jaccard_similarity(a, b, ngram=3)
    assert 0.0 < score < 1.0


def test_jaccard_both_empty_returns_one() -> None:
    """둘 다 빈 토큰 — 폴백 1.0 (수학적 정의 확장)."""
    assert text_similarity.jaccard_similarity("", "", ngram=3) == 1.0
    assert text_similarity.jaccard_similarity("   ", "\n", ngram=3) == 1.0


def test_jaccard_one_empty_returns_zero() -> None:
    assert text_similarity.jaccard_similarity("hello world", "", ngram=3) == 0.0
    assert text_similarity.jaccard_similarity("", "hello world", ngram=3) == 0.0


def test_jaccard_short_text_falls_back_to_unigram() -> None:
    """ngram=3 보다 짧은 토큰 — n=1 단어 단위 fallback."""
    a = "둘 단어"
    b = "둘 단어"
    assert text_similarity.jaccard_similarity(a, b, ngram=3) == 1.0


def test_jaccard_default_ngram_is_three() -> None:
    """기본 인자 검증 — 명시 안 해도 ngram=3."""
    a = "다이어트 한의원 천안 추천 후기 효과 좋은 곳"
    b = "다이어트 한의원 천안 추천 후기 효과 좋은 곳"
    assert text_similarity.jaccard_similarity(a, b) == 1.0


def test_jaccard_returns_float_in_range() -> None:
    """score 항상 [0.0, 1.0] 범위."""
    a = "한 둘 셋 넷 다섯"
    b = "한 셋 다섯"
    score = text_similarity.jaccard_similarity(a, b, ngram=2)
    assert 0.0 <= score <= 1.0


# ── fetch_content_md ──


def test_fetch_content_md_returns_text() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"content_md": "# 본문 내용\n\n첫 문단."}]
    )
    with patch("application.text_similarity.get_client", return_value=mock_client):
        result = text_similarity.fetch_content_md("gen-1")
    assert result == "# 본문 내용\n\n첫 문단."


def test_fetch_content_md_none_id_returns_none() -> None:
    """generated_content_id None → 즉시 None (Supabase 호출 0)."""
    with patch("application.text_similarity.get_client") as gc:
        result = text_similarity.fetch_content_md(None)
    assert result is None
    gc.assert_not_called()


def test_fetch_content_md_missing_row_returns_none() -> None:
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    with patch("application.text_similarity.get_client", return_value=mock_client):
        result = text_similarity.fetch_content_md("gen-missing")
    assert result is None


def test_fetch_content_md_supabase_failure_returns_none() -> None:
    """Supabase 호출 실패 — graceful None (logger.warning)."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
        "supabase down"
    )
    with patch("application.text_similarity.get_client", return_value=mock_client):
        result = text_similarity.fetch_content_md("gen-1")
    assert result is None


def test_fetch_content_md_non_string_value_returns_none() -> None:
    """content_md 가 None / dict 등 비-문자열 → None."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[{"content_md": None}]
    )
    with patch("application.text_similarity.get_client", return_value=mock_client):
        result = text_similarity.fetch_content_md("gen-1")
    assert result is None
