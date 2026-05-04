# Batch Domain

키워드 배치 운영 격리 도메인. SPEC-BATCH.md 구현.

## 🔴 격리 원칙

- 다른 도메인 import **절대 금지** — `architecture-check.sh` 의 `STAGE_ORDER[batch]=0`
- CSV 파싱 / Supabase CRUD / 모델만 책임
- 단일 흐름 호출 (`run_pipeline`/`run_analyze_only`/`run_generate_only`) 은
  **`application/batch_orchestrator.py`** 가 합성 (도메인 안에서 호출 X)

## 파일 책임

- `model.py` — `KeywordBatch`, `KeywordBatchItem`, `BatchEnqueueResult`,
  예외 (`CsvParseError`, `NotSupportedYetError`), Literal 타입 (`Mode`,
  `Operation`, `ItemStatus` 등)
- `csv_parser.py` — CSV 텍스트 → `(created, skipped, failed)`. 검증·중복 제거·폴백
- `storage.py` — Supabase CRUD. payload 변환은 본 파일에만. `update_item_status` 는 상태 머신, `update_item_result` 는 결과 메타(pattern_card_id/generated_content_id/compliance_passed/search_volume/difficulty_grade) 책임 분리 (Phase B7+B8). `find_primary_in_cluster(batch_id, cluster_id)` 는 cluster 재사용 정책의 primary 조회 단일 출처 (Phase B8). cluster_dedupe **default OFF** — 본문 유사도 1페이지 노출 리스크 보수 처리
- Phase B9 추가 — `update_item_review(*, review_status, status, reviewer)` 는 검수 액션 메타 갱신 (approve 시 status 동시 전환). `list_review_pending_items` 는 검수 큐 데이터 소스. `ItemStatus` 에 `ready_to_publish` 추가 (succeeded 의미 분리 — analyze 만 끝난 item 만 succeeded, generate/pipeline + compliance_passed=True 는 ready_to_publish, False/None 은 needs_review 안전망). `ready_to_publish_count` 는 DB 컬럼 미존재 — `count_items_by_status` 가 매번 in-memory 재집계. **운영 철학**: 후보 키워드는 모두 발행 대상, needs_review 는 폐기가 아닌 발행 전 대기. 핵심 액션 approve/needs_fix, reject 는 예외 (UI dropdown 보조)

## 핵심 규칙

- 모든 함수 Pydantic 반환. raw dict / stdout / 파일 경로 반환 금지
- 함수 30줄 이내 (storage 의 row 변환 헬퍼는 예외 — 매핑성 코드)
- `print()` 금지, `logging` 사용
- mode 검증은 application 레이어 — 도메인은 모든 mode 값을 받아 저장만

## 금지

- `domain/batch → domain/*` import (격리 위반, 훅 차단)
- `application/orchestrator` 호출 — application 책임
- 단일 `run_pipeline` 직접 호출 (격리 위반)

## 참조

- SPEC-BATCH.md
- application/batch_orchestrator.py (합성 책임)
- tasks/todo.md "Batch Pipeline MVP"
