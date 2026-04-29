"""키워드 노출 난이도 분석 CLI.

얇은 argparse 래퍼 — `application.keyword_difficulty_orchestrator` 호출.

사용 예:
    python scripts/analyze_keyword_difficulty.py --keyword 다이어트한약
    python scripts/analyze_keyword_difficulty.py --keyword kw1 kw2 kw3
    python scripts/analyze_keyword_difficulty.py --file keywords.txt
    python scripts/analyze_keyword_difficulty.py --file keywords.txt --no-persist
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from application.keyword_difficulty_orchestrator import (
    analyze_keyword,
    batch_analyze_keywords,
)
from domain.keyword_difficulty.model import KeywordDifficulty


def _read_keywords_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"파일 없음: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _print_table(results: list[KeywordDifficulty]) -> None:
    if not results:
        print("결과 없음")
        return
    header = f"{'키워드':25} {'등급':9} {'점수':>7} {'B':>3} {'D':>3} {'T':>4}"
    print(header)
    print("-" * len(header))
    for r in sorted(results, key=lambda x: (x.grade.value, -x.score)):
        c = r.composition
        print(
            f"{r.keyword[:25]:25} {r.grade.value:9} {r.score:>7} "
            f"{c.blog_slots:>3} {c.spam_cards:>3} {c.total_cards:>4}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="네이버 SERP 분석 → 블로그 노출 난이도 등급 (tasks/todo.md Phase K)",
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--keyword", nargs="+", help="키워드 1개 또는 다수 (공백 구분)")
    grp.add_argument("--file", type=Path, help="개행 구분 키워드 파일")
    parser.add_argument(
        "--parallel", type=int, default=3, help="병렬 분석 수 (기본 3, Bright Data rate 보호)"
    )
    parser.add_argument(
        "--no-persist", action="store_true", help="Supabase 저장 스킵 (분석만 수행)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    keywords: list[str] = args.keyword if args.keyword else _read_keywords_file(args.file)
    if not keywords:
        print("키워드가 비어 있음", file=sys.stderr)
        return 2

    persist = not args.no_persist

    if len(keywords) == 1:
        result = analyze_keyword(keywords[0], persist=persist)
        _print_table([result])
        return 0

    results = batch_analyze_keywords(keywords, parallel=args.parallel, persist=persist)
    _print_table(results)
    return 0 if len(results) == len(keywords) else 1


if __name__ == "__main__":
    sys.exit(main())
