-- 2026-05-14 — keyword_batch_items.failure_category 컬럼 추가.
-- /insights 키워드 단위 행 뷰 + 실패 사유 집계용. error 컬럼은 원문 보존 (디버깅용).
-- enum 값: PREFILTER_VOLUME / PREFILTER_DIFFICULTY / SERP_INSUFFICIENT /
--          SCRAPE_INSUFFICIENT / COMPLIANCE_FAILED / BODY_SIMILARITY_HIGH / EXCEPTION
-- idempotent — 이미 존재하면 noop.

alter table keyword_batch_items
    add column if not exists failure_category text;

-- 부분 인덱스: failure status row 에서만 sparse 하게 (성능 최적화).
-- needs_review 도 포함 — BODY_SIMILARITY_HIGH / COMPLIANCE_FAILED 가 needs_review 에 마킹.
create index if not exists idx_keyword_batch_items_failure_cat
    on keyword_batch_items (status, failure_category)
    where status in ('failed', 'skipped', 'needs_review');
