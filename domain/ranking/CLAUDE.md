# Ranking Domain

네이버 SERP 순위 추적. SPEC-RANKING.md 구현. **실측 피드백 루프 MVP**.

## 🔴 최상위 원칙

### 1. 도메인 격리 절대 준수

- `domain/ranking/*` 는 `domain/crawler/*` 를 **import 하지 않는다**
- SERP fetch/parse 는 `tracker.find_position` 의 인자(`serp_fetcher`, `serp_parser`)로 의존성 주입
- 두 도메인의 합성은 `application/ranking_orchestrator.py` 가 책임
- `architecture-check.sh` 에서 자동 차단 (STAGE_ORDER[ranking]=0 격리 도메인)

### 2. URL 정규화 단일 출처 = `url_match.py`

- 다른 모듈은 `normalize_blog_url`, `urls_match` 호출만
- 직접 정규식·파싱 금지

### 3. `BLOG_POST_URL_RE` 의도적 복제

- `serp_collector.py` 와 동일 패턴이 `url_match.py` 에 의도적으로 복제됨
- 도메인 격리 원칙 때문에 복제가 합리적이지만 **수동 동기화 필수**
- serp_collector 정규식 변경 시 본 파일도 같이 갱신
- tasks/lessons.md 에 패턴 기록

### 4. 스냅샷은 append-only

- `ranking_snapshots` row 는 update/delete 안 함
- 모든 측정은 시계열 누적
- 잘못된 측정도 그대로 남기고, 별도 후속 측정으로 보정

### 5. 멱등 등록

- 동일 URL 재등록 → `RankingDuplicateUrlError` 를 application 이 catch 해 기존 row 반환

## 파일 책임

- `model.py` — `Publication`, `RankingSnapshot`, `RankingTimeline`, `RankingCheckSummary`, 예외 2종 Pydantic 모델
- `url_match.py` — `BLOG_POST_URL_RE` (의도적 복제), `normalize_blog_url`, `urls_match`
- `tracker.py` — `find_position` (DI 패턴, crawler import 금지)
- `storage.py` — Supabase CRUD (publications + ranking_snapshots)

## 핵심 규칙

- 모든 함수 Pydantic 반환. raw dict / stdout / 파일 경로 반환 금지
- 함수 30줄 이내, 파일 300줄 이내
- LLM 호출 0건 — 결정적 매칭이라 불필요. 비용 효율 매우 높음
- `print()` 금지, `logging` 사용
- 모든 외부 호출 (Supabase, SERP fetcher) 은 호출자(application)가 timeout·재시도 책임

## 금지

- `domain/ranking → domain/crawler` 직접 import (격리 위반, 훅 차단)
- 정규식·URL 매칭 로직을 url_match 외부에 작성
- ranking_snapshots row update/delete (append-only 위반)
- LLM 호출 (불필요, 비용 누수)
- raw dict 노출 (Pydantic 강제)

## 참조

- SPEC-RANKING.md
- domain/crawler/CLAUDE.md (재사용 자산)
- application/CLAUDE.md (오케스트레이션 패턴)
- tasks/lessons.md (정규식 복제 동기화 메모)
