"""단계별 실행 헬퍼. orchestrator 가 호출.

각 함수는 해당 도메인 함수를 wrap 하고 ProgressReporter 를 호출한다.
파일 저장과 Supabase 저장도 여기서 수행 (도메인은 순수 계산만).

MVP 스켈레톤 — 1단계 크롤러부터 순차적으로 채운다.
"""

from __future__ import annotations

# NOTE:
# 이 파일은 각 단계의 헬퍼 함수를 모아두는 곳이다.
# 단계별 구현 순서는 SPEC.md §8 개발 순서 참조.
#
# 예시 시그니처 (실제 타입은 도메인 모델 구현 후 import):
#
# from application.progress import ProgressReporter
# from domain.crawler.model import SerpResults, BlogPage
#
# def run_stage_serp_collection(
#     keyword: str,
#     reporter: ProgressReporter,
# ) -> SerpResults:
#     """[1] SERP 수집."""
#     reporter.stage_start("serp_collection")
#     # ... 도메인 호출 ...
#     reporter.stage_end("serp_collection", {"count": ...})
#     return result
#
# def run_stage_page_scraping(
#     serp: SerpResults,
#     reporter: ProgressReporter,
# ) -> list[BlogPage]: ...
#
# def run_stage_physical_extraction(...): ...
# def run_stage_semantic_extraction(...): ...
# def run_stage_appeal_extraction(...): ...
# def run_stage_cross_analysis(...): ...
# def run_stage_outline_generation(...): ...
# def run_stage_body_generation(...): ...
# def run_stage_compliance_check(...): ...
# def run_stage_naver_html_assembly(...): ...
