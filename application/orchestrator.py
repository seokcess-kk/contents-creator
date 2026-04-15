"""파이프라인 use case. CLI 와 Phase 2 FastAPI 가 공통으로 호출하는 진입점.

⚠️ 함수 시그니처는 SPEC.md §12-4 불변 규칙.
변경하려면 SPEC.md 먼저 수정 후 동기화할 것.

현재 MVP 스켈레톤 — 각 함수 본문은 해당 단계 구현 시 채운다:
  - run_pipeline: 1~6단계 완료 후 최종 통합 (개발 순서 7단계)
  - run_analyze_only: 3단계 완료 시
  - run_generate_only: 4단계 완료 시
  - run_validate_only: 5단계 완료 시
"""

from __future__ import annotations

from pathlib import Path

from application.models import (
    AnalyzeResult,
    GenerateResult,
    PipelineResult,
    ValidateResult,
)
from application.progress import LoggingProgressReporter, ProgressReporter


def run_pipeline(
    keyword: str,
    reporter: ProgressReporter | None = None,
    pattern_card_path: Path | None = None,
) -> PipelineResult:
    """전체 8단계 파이프라인 실행.

    Args:
        keyword: 타겟 네이버 검색 키워드
        reporter: 진행 리포터. None 이면 LoggingProgressReporter 기본값
        pattern_card_path: 지정 시 기존 패턴 카드 재사용, None 이면 [1]~[5] 분석부터 실행

    Returns:
        PipelineResult — 실행 결과. 실패도 예외 대신 status=FAILED 로 반환
    """
    _reporter = reporter or LoggingProgressReporter()
    _ = (_reporter, keyword, pattern_card_path)
    raise NotImplementedError("run_pipeline 은 1~6단계 도메인 구현 완료 후 7단계에서 채운다")


def run_analyze_only(
    keyword: str,
    reporter: ProgressReporter | None = None,
) -> AnalyzeResult:
    """[1]~[5] 분석 파이프라인만 실행.

    결과: pattern-card.json 파일 + Supabase pattern_cards 레코드
    """
    _reporter = reporter or LoggingProgressReporter()
    _ = (_reporter, keyword)
    raise NotImplementedError("run_analyze_only 는 3단계 구현 시 채운다")


def run_generate_only(
    keyword: str | None = None,
    pattern_card_path: Path | None = None,
    reporter: ProgressReporter | None = None,
) -> GenerateResult:
    """[6]~[9] 생성 파이프라인만 실행.

    keyword 지정 시 DB 에서 최신 패턴 카드 조회.
    pattern_card_path 지정 시 해당 파일 사용.
    """
    if keyword is None and pattern_card_path is None:
        raise ValueError("keyword 또는 pattern_card_path 중 하나는 필요")

    _reporter = reporter or LoggingProgressReporter()
    _ = (_reporter, keyword, pattern_card_path)
    raise NotImplementedError("run_generate_only 는 4단계 구현 시 채운다")


def run_validate_only(
    content_path: Path,
    reporter: ProgressReporter | None = None,
) -> ValidateResult:
    """[8] 의료법 검증만 실행.

    기존 원고 파일을 읽어 8개 카테고리 기준 검증·자동 수정.
    """
    _reporter = reporter or LoggingProgressReporter()
    _ = (_reporter, content_path)
    raise NotImplementedError("run_validate_only 는 5단계 구현 시 채운다")
