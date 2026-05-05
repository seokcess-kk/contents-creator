"""SPEC-BATCH §3 Phase 4 PR2 — publication 자동 등록 (opt-in).

운영 철학 §0: 후보 키워드 모두 발행 대상이지만, **실제 발행은 운영자가 네이버
블로그 직접 수행**. publications 등록도 명시적 opt-in (`KeywordBatch.auto_publish_enabled`).

활성 조건:
- `keyword_batches.auto_publish_enabled = true`
- item.status = 'ready_to_publish'
- item.target_url IS NOT NULL (운영자가 CSV 에 미리 적었거나 검수 큐에서 등록)

동작:
- 각 item 별로 `application.ranking_orchestrator.register_publication` 호출 (멱등)
- 충돌 시 (UNIQUE(url)) 기존 publication 반환 — `_attach_batch_item` 이
  keyword_batch_items.publication_id 를 자동 백필
- 등록된 publication 은 `/rankings` 추적 사이클에 자동 진입 (외부 cron)

호출 흐름:
- `recompute_batch_status` 의 completed 첫 진입 시 자동 (batch.auto_publish_enabled=True)
- CLI: `scripts/run_batch.py --auto-publish <batch_id>`
- Web API: `POST /batches/{id}/auto-publish`

`auto_publish_enabled=False` 또는 정책 미충족 item 은 자동 skip — 운영자가
검수 큐 / publish 페이지에서 수동 URL 등록.
"""

from __future__ import annotations

import logging
from typing import Any

from application import ranking_orchestrator
from domain.batch import storage
from domain.ranking.model import RankingDuplicateUrlError

logger = logging.getLogger(__name__)


def auto_publish_ready_items(batch_id: str) -> dict[str, Any]:
    """batch 의 ready_to_publish + target_url 인 item 들을 publications 자동 등록.

    `batch.auto_publish_enabled=False` → 즉시 noop ({registered:0, skipped:0, failed:0,
    skipped_reason:"auto_publish_disabled"}).

    각 item:
      - target_url 부재 → skipped (reason: "no_target_url")
      - 이미 publication_id 있음 → skipped (reason: "already_linked")
      - register_publication 성공 → registered (publication_id 회수)
      - URL 형식 오류 / 외부 통신 실패 → failed

    멱등 — 같은 batch 두 번 호출 시 두 번째는 모두 already_linked 로 skipped.

    반환:
        {
            "registered": int,
            "skipped": int,
            "skipped_reason": str | None,  # 전체 noop 케이스만 (batch 단위)
            "failed": int,
            "items": list[dict],  # 상세 (operations dashboard 노출용)
        }
    """
    batch = storage.get_batch(batch_id)
    if batch is None:
        raise ValueError(f"batch 미존재: {batch_id}")

    if not batch.auto_publish_enabled:
        logger.info(
            "auto_publish.disabled batch_id=%s — auto_publish_enabled=False",
            batch_id,
        )
        return {
            "registered": 0,
            "skipped": 0,
            "skipped_reason": "auto_publish_disabled",
            "failed": 0,
            "items": [],
        }

    candidates = storage.list_items(batch_id, status="ready_to_publish", limit=10_000)
    registered = 0
    skipped = 0
    failed = 0
    item_results: list[dict[str, Any]] = []

    for item in candidates:
        if item.id is None:
            continue
        # 1) target_url 부재 — 운영자가 검수 큐에서 수동 등록 필요
        if not item.target_url:
            skipped += 1
            item_results.append(
                {
                    "item_id": item.id,
                    "keyword": item.keyword,
                    "result": "skipped",
                    "reason": "no_target_url",
                }
            )
            continue
        # 2) 이미 publication_id 채워짐 (멱등) — 백필 / 수동 등록 / 직전 호출
        if item.publication_id is not None:
            skipped += 1
            item_results.append(
                {
                    "item_id": item.id,
                    "keyword": item.keyword,
                    "result": "skipped",
                    "reason": "already_linked",
                    "publication_id": item.publication_id,
                }
            )
            continue
        # 3) register_publication 호출 (멱등 + _attach_batch_item 가 publication_id 백필)
        try:
            pub = ranking_orchestrator.register_publication(
                keyword=item.keyword,
                url=item.target_url,
                slug=None,
                job_id=item.job_id,
            )
        except (ValueError, RankingDuplicateUrlError) as exc:
            failed += 1
            item_results.append(
                {
                    "item_id": item.id,
                    "keyword": item.keyword,
                    "result": "failed",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            logger.warning(
                "auto_publish.register_failed item_id=%s keyword=%s url=%s err=%s",
                item.id,
                item.keyword,
                item.target_url,
                exc,
            )
            continue
        except Exception as exc:
            failed += 1
            item_results.append(
                {
                    "item_id": item.id,
                    "keyword": item.keyword,
                    "result": "failed",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            logger.exception("auto_publish.unexpected item_id=%s", item.id)
            continue

        registered += 1
        item_results.append(
            {
                "item_id": item.id,
                "keyword": item.keyword,
                "result": "registered",
                "publication_id": pub.id,
                "url": pub.url,
            }
        )
        logger.info(
            "auto_publish.registered item_id=%s keyword=%s publication_id=%s url=%s",
            item.id,
            item.keyword,
            pub.id,
            pub.url,
        )

    logger.info(
        "auto_publish.done batch_id=%s registered=%d skipped=%d failed=%d",
        batch_id,
        registered,
        skipped,
        failed,
    )
    return {
        "registered": registered,
        "skipped": skipped,
        "skipped_reason": None,
        "failed": failed,
        "items": item_results,
    }


__all__ = ["auto_publish_ready_items"]
