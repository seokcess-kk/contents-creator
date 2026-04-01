"""분석만 실행. 키워드 → 크롤링 → 패턴 카드 생성.

사용법:
    python scripts/analyze.py --keyword "강남 피부과" --top-n 10
"""

from __future__ import annotations

import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("analyze")


def main() -> None:
    parser = argparse.ArgumentParser(description="키워드 분석 → 패턴 카드 생성")
    parser.add_argument("--keyword", required=True, help="검색 키워드")
    parser.add_argument("--top-n", type=int, default=10, help="크롤링 상위 N개")
    args = parser.parse_args()

    # 크롤링
    from domain.crawler.pipeline import run_crawl

    crawl_result = run_crawl(args.keyword, top_n=args.top_n)
    successful = [p for p in crawl_result.posts if p.success and p.raw_html]

    if not successful:
        logger.error("크롤링 성공 0건")
        return

    # 분석
    from domain.analysis.copy_analyzer import aggregate_l2, analyze_copy_single
    from domain.analysis.pattern_card import build_pattern_card
    from domain.analysis.structure_analyzer import aggregate_l1, analyze_structure
    from domain.analysis.visual_analyzer import aggregate_visual, analyze_visual_dom

    l1 = aggregate_l1([analyze_structure(p.raw_html) for p in successful])
    l2 = aggregate_l2([analyze_copy_single(p.title, p.text_content) for p in successful])
    visual = aggregate_visual(
        [analyze_visual_dom(p.raw_html) for p in successful],
        [{} for _ in successful],
    )
    card = build_pattern_card(args.keyword, l1, l2, visual)

    # 저장
    from domain.common.config import settings

    output_path = settings.workspace_dir / "03_pattern" / "pattern_card.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(card.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("패턴 카드 저장: %s", output_path)


if __name__ == "__main__":
    main()
