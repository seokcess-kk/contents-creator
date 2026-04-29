"""브랜드 미디어 자산 삭제 CLI.

얇은 argparse 래퍼 — `domain.brand_card.storage.delete_media_asset` 호출.
brand_media_assets 1행 제거. 파일 자체는 별도 정책으로 관리(미삭제).
"""

from __future__ import annotations

import argparse
import logging
import sys

from domain.brand_card.storage import delete_media_asset, get_media_asset


def main() -> int:
    parser = argparse.ArgumentParser(
        description="브랜드 미디어 자산 삭제 (DB 행만)",
    )
    parser.add_argument("--asset-id", required=True, help="삭제할 자산 ID (UUID)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="확인 프롬프트 없이 삭제 진행",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    asset = get_media_asset(args.asset_id)
    if asset is None:
        print(f"자산 미존재: {args.asset_id}", file=sys.stderr)
        return 2

    print(f"삭제 대상: id={asset.id} type={asset.type} title={asset.title}")
    if not args.yes:
        answer = input("정말 삭제하시겠습니까? (y/N): ").strip().lower()
        if answer != "y":
            print("취소됨")
            return 1

    ok = delete_media_asset(args.asset_id)
    if not ok:
        print(f"삭제 실패: {args.asset_id}", file=sys.stderr)
        return 1
    print(f"삭제 완료: {args.asset_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
