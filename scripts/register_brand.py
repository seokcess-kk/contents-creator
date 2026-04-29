"""브랜드 등록 CLI.

얇은 argparse 래퍼 — 실제 저장은 `domain.brand_card.storage.insert_brand`.
slug UNIQUE 제약 충돌 시 BrandSlugConflictError 로 종료.
"""

from __future__ import annotations

import argparse
import logging
import sys

from domain.brand_card.model import BrandProfile
from domain.brand_card.storage import BrandSlugConflictError, get_brand_by_slug, insert_brand


def main() -> int:
    parser = argparse.ArgumentParser(
        description="브랜드 등록 (SPEC-BRAND-CARD §4 [B1])",
    )
    parser.add_argument("--name", required=True, help="브랜드 표시명 (예: '서울본클리닉')")
    parser.add_argument("--slug", required=True, help="URL/디렉토리용 slug (예: 'seoul-bon')")
    parser.add_argument("--homepage", required=True, help="브랜드 홈페이지 URL")
    parser.add_argument("--locale", default="ko-KR", help="기본값 ko-KR")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    existing = get_brand_by_slug(args.slug)
    if existing is not None:
        print(f"이미 등록된 slug: {args.slug} → brand_id={existing.id}", file=sys.stderr)
        return 2

    profile = BrandProfile(
        name=args.name,
        slug=args.slug,
        homepage_url=args.homepage,
        locale=args.locale,
    )
    try:
        saved = insert_brand(profile)
    except BrandSlugConflictError as exc:
        print(f"slug 충돌: {exc}", file=sys.stderr)
        return 2

    print(f"브랜드 등록 완료: brand_id={saved.id} slug={saved.slug} name={saved.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
