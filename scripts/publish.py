"""자동 발행 CLI — 얇은 argparse 래퍼.

실제 로직은 `application.publishing_orchestrator.publish_from_output_dir`.

PoC 사용 예시 (Phase AP-A):

    # 1. 우선 dry_run 으로 documentModel 확인
    python scripts/publish.py \\
        --slug 다이어트한의원 \\
        --ts 20260506-143336 \\
        --channel-id <blog_channels.id UUID> \\
        --keyword "다이어트한의원" \\
        --dry-run

    # 2. PUBLISHING_ENABLED=true 환경에서 실제 발행
    PUBLISHING_ENABLED=true python scripts/publish.py \\
        --slug 다이어트한의원 \\
        --ts 20260506-143336 \\
        --channel-id <blog_channels.id UUID> \\
        --keyword "다이어트한의원"

운영 가드:
    - PUBLISHING_ENABLED=false (default) 면 NaverBlogPublisher 인스턴스 거부
    - --dry-run 시 RabbitWrite POST 호출 없이 documentModel JSON 만 저장
    - --no-register 시 발행 성공해도 register_publication 호출 X

채널 ID: web/api/routers/blog_channels.py 의 GET /blog-channels 또는 frontend
/blogs 페이지에서 확인. PoC 단계에서는 등록된 5채널 중 1개를 명시 지정.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from application.publishing_orchestrator import publish_from_output_dir
from domain.blog_channel import storage as channel_storage
from domain.publishing.model import PublishingDisabledError, PublishingError


def _non_empty(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise argparse.ArgumentTypeError("값은 공백일 수 없습니다")
    return stripped


def _resolve_output_dir(slug: str, ts: str | None) -> Path:
    """`output/{slug}/{ts}/` 또는 `output/{slug}/latest/` 해석. 미존재 시 raise."""
    project_root = Path(__file__).resolve().parents[1]
    base = project_root / "output" / slug
    if not base.exists():
        raise FileNotFoundError(f"slug 디렉터리 미존재: {base}")
    if ts is None:
        # 가장 최신 타임스탬프 디렉터리 자동 선택
        candidates = sorted(
            (p for p in base.iterdir() if p.is_dir() and p.name[0].isdigit()),
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"{base} 안에 타임스탬프 디렉터리 없음")
        return candidates[0]
    target = base / ts
    if not target.exists():
        raise FileNotFoundError(f"타임스탬프 디렉터리 미존재: {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="네이버 블로그 자동 발행 (Phase AP-A PoC) — RabbitWrite POST 1회",
    )
    parser.add_argument("--slug", type=_non_empty, required=True, help="output/<slug>/ 디렉터리명")
    parser.add_argument(
        "--ts",
        type=str,
        default=None,
        help="타임스탬프 디렉터리. 미지정 시 가장 최신 자동 선택",
    )
    parser.add_argument(
        "--channel-id",
        type=_non_empty,
        required=True,
        help="blog_channels.id (UUID). /blogs 페이지 또는 GET /blog-channels 로 확인",
    )
    parser.add_argument(
        "--keyword",
        type=_non_empty,
        required=True,
        help="추적용 키워드 — publishing_attempts + register_publication 에 기록",
    )
    parser.add_argument("--job-id", type=str, default=None, help="원본 job_id (선택)")
    parser.add_argument(
        "--tags",
        type=str,
        default=None,
        help="발행 태그 (쉼표 구분). 미지정 시 outline.json 의 suggested_tags 사용",
    )
    parser.add_argument(
        "--category-no", type=int, default=0, help="네이버 카테고리 ID (default 0=기본)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="RabbitWrite POST 호출 없이 documentModel JSON 만 _publish_dryrun.json 으로 저장",
    )
    parser.add_argument(
        "--no-register",
        action="store_true",
        help="발행 성공해도 register_publication 호출 안 함 (순위 추적 진입 X)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("scripts.publish")

    # 채널 조회
    try:
        channel = channel_storage.get_channel(args.channel_id)
    except Exception as exc:
        logger.error("blog_channels 조회 실패: %s", exc)
        return 2
    if channel is None:
        logger.error("channel_id 미존재: %s", args.channel_id)
        return 2

    # output 디렉터리 해석
    try:
        output_dir = _resolve_output_dir(args.slug, args.ts)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    parsed_tags: list[str] | None = None
    if args.tags:
        parsed_tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    logger.info(
        "publish.start slug=%s ts=%s channel=%s(%s) dry_run=%s",
        args.slug,
        output_dir.name,
        channel.name,
        channel.blog_id,
        args.dry_run,
    )

    try:
        result = publish_from_output_dir(
            output_dir=output_dir,
            channel=channel,
            keyword=args.keyword,
            job_id=args.job_id,
            tags=parsed_tags,
            category_no=args.category_no,
            dry_run=args.dry_run,
            register_after_publish=not args.no_register,
        )
    except PublishingDisabledError as exc:
        logger.error("발행 비활성: %s", exc)
        return 3
    except PublishingError as exc:
        logger.error("발행 실패: %s", exc)
        return 1
    except Exception as exc:
        logger.exception("예기치 못한 에러: %s", exc)
        return 1

    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
