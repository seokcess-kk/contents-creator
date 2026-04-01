"""생성만 실행. 기존 패턴 카드 + 프로필 → 콘텐츠 생성.

사용법:
    python scripts/generate.py --pattern-card pattern_card.json --profile-id xxx
"""

from __future__ import annotations

import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("generate")


def main() -> None:
    parser = argparse.ArgumentParser(description="패턴 카드 기반 콘텐츠 생성")
    parser.add_argument("--pattern-card", required=True, help="패턴 카드 JSON 경로")
    parser.add_argument("--profile-id", required=True, help="클라이언트 프로필 ID")
    parser.add_argument("--keyword", help="키워드 (패턴 카드에서 자동 추출)")
    args = parser.parse_args()

    from pathlib import Path

    from domain.analysis.model import PatternCard
    from domain.profile.repository import get_profile_repository

    # 패턴 카드 로드
    card_path = Path(args.pattern_card)
    card_data = json.loads(card_path.read_text(encoding="utf-8"))
    pattern_card = PatternCard.model_validate(card_data)
    keyword = args.keyword or pattern_card.keyword

    # 프로필 로드
    profile = get_profile_repository().get(args.profile_id)
    if not profile:
        logger.error("프로필을 찾을 수 없습니다: %s", args.profile_id)
        return

    # 생성
    from domain.generation.design_card import generate_cta_card, generate_header_card
    from domain.generation.image_generator import generate_image_prompts
    from domain.generation.model import GeneratedContent
    from domain.generation.seo_writer import generate_seo_text
    from domain.generation.variation_engine import format_variation_preview, recommend_variation

    variation = recommend_variation(pattern_card)
    print(format_variation_preview(variation))
    input("Enter로 승인:")

    title, seo_text = generate_seo_text(keyword, pattern_card, profile, variation)
    header = generate_header_card(keyword, title, pattern_card, profile)
    cta = generate_cta_card(pattern_card, profile)
    prompts = generate_image_prompts(keyword, pattern_card, profile)

    content = GeneratedContent(
        keyword=keyword,
        title=title,
        seo_text=seo_text,
        variation_config=variation,
        design_cards=[header, cta],
        ai_image_prompts=prompts,
    )

    # 조합
    from domain.composer.assembler import assemble

    output = assemble(content)
    logger.info("완료: %s", output.output_dir)


if __name__ == "__main__":
    main()
