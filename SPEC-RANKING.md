# 순위 추적 시스템 (Ranking Tracker) — Spec v1

본 문서는 contents-creator 의 **실측 피드백 루프 MVP** 명세다.
SEO 트랙(SPEC-SEO-TEXT.md)·브랜드 카드 트랙(SPEC-BRAND-CARD.md)과 **병행되는 보조 트랙**이며, 의존 방향은 단방향(ranking → publish 결과만 참조).

작성: 2026-04-24
연관: tasks/todo.md "Ranking Tracker MVP" 섹션, application/CLAUDE.md, domain/compliance/CLAUDE.md

---

## 1. 목적

생성·발행한 SEO 원고의 **네이버 검색 결과 순위를 시계열로 측정**해 다음을 가능하게 한다:

- 어떤 패턴 카드 구성(섹션·DIA+·이미지·키워드 밀도)이 실제 노출 성과로 이어지는가의 데이터 누적
- 동일 키워드 재작성 의사결정 근거 (현재 위치 기반)
- Phase 2 자동 학습 루프 (효과 있던 패턴에 가중치)의 데이터 토대

명시적 비목표:
- **자동 발행 X** — 사용자가 네이버 블로그에 직접 발행 후 URL 만 등록
- **순위 분석/예측 X** — MVP 는 측정·기록까지만. 학습은 Phase 2
- **타사 SEO 도구 대체 X** — 자체 생성한 글의 자체 순위 추적 한정

---

## 2. 파이프라인

```
[등록]    사용자가 발행 후 URL 입력
   │      → publications row insert (멱등: 동일 url 재호출은 기존 row 반환)
   │
   ▼
[수집]    매일 09:00 KST 모든 활성 publication 순회
   │      → 키워드 SERP 재크롤 (Bright Data Web Unlocker, 기존 자산 재사용)
   │      → 등록 URL 매칭
   │      → ranking_snapshots row insert
   │
   ▼
[조회]    Web UI / API / CLI 로 시계열 조회
          → 결과 페이지 + /rankings 통합 페이지
```

**3개 진입점** (등록/즉시 체크/조회):
- API (`/api/rankings/*`) — 프론트엔드/외부 통합
- CLI (`scripts/register_publication.py`, `scripts/check_rankings.py`) — 운영·일회성 작업
- 스케줄러 (APScheduler) — 매일 자동 수집

---

## 3. 각 단계 상세

### [등록] register_publication

**입력**: `keyword`, `url` (필수), `slug` / `job_id` / `published_at` (선택)
**처리**:
1. `domain/ranking/url_match.normalize_blog_url(url)` 로 정규화
   - 스킴 없으면 `https://` 보정
   - `blog.naver.com/{userid}/{postid}` → `m.blog.naver.com/{userid}/{postid}` (모바일 통일)
   - 트레일링 슬래시·쿼리스트링 제거
2. `domain/ranking/storage.insert_publication(publication)` — Supabase publications row insert
3. UNIQUE(url) 충돌 시 기존 row 반환 (멱등). `RankingDuplicateUrlError` 는 application 레이어에서만 catch
**출력**: `Publication` Pydantic 모델

**slug 의 의미**:
- 본 프로젝트로 발행한 글 → `output/{slug}/` 디렉터리 매칭용으로 채움. 결과 페이지 (`/results/{slug}`) 와 자동 연결
- 외부 URL 추적 (직접 발행 안 한 글, 경쟁사 글 등) → `slug` 생략 (NULL). `/rankings` 대시보드에만 노출, 결과 페이지 링크 없음

### [수집] check_rankings_for_publication

**입력**: `publication_id`
**처리**:
1. publication 조회 (없으면 명시적 ValueError)
2. `domain.crawler.serp_collector.build_main_search_url(keyword)` 로 통합검색 메인 URL 생성 (`?where=nexearch&query=`). 사용자가 보는 그대로의 통합검색 페이지를 받아온다 (블로그 탭이 아님).
3. `BrightDataClient` 으로 SERP HTML fetch
4. `domain/ranking/serp_parser.parse_integrated_serp(html)` 로 섹션별 콘텐츠 URL 리스트 추출
   - **그룹핑 키**: `data-meta-area` (네이버의 논리적 섹션 ID). 같은 area 가 연속되면 한 섹션으로 묶음
   - **섹션 라벨**: `_AREA_NAME_MAP` 으로 area→이름 매핑 (예: `rrB_hdR`→인플루언서, `rrB_bdR`→VIEW, `ugB_bsR`→인기글, `nws_all`→뉴스). 매핑 실패 시 `data-block-id` 다수결 폴백
   - **제외**: 광고(`pcad`/`powerlink`/`adB_*`), 플레이스(`plB_*`), 쇼핑(`shB_*`) area 자동 스킵
   - **노이즈 제거**: `fds-ugc-after-article-list` (이 블로거의 다른 글), `fds-ugc-reply` (댓글), `fds-comps-keyword-chip` (키워드 칩) 제거
   - **URL 필터**: 네이버 콘텐츠 leaf URL 패턴(블로그 포스트·카페 글·인플루언서 contents 등)만 통과. 작성자 프로필 등 보조 링크는 패턴 미스로 자동 제외
   - **작성자 dedupe**: fender-root 내부 한정. 한 template 안에 carousel 형태로 여러 글이 나열되면 작성자별 1개로 압축. 별도 fender-root 끼리는 dedupe 안 함
5. `domain/ranking/tracker.find_position(...)` 호출:
   - URL 정규화 후 모든 섹션의 URL 과 순회 비교
   - 매칭되면 `(section, position)` 반환, 어느 섹션에도 없으면 `(None, None)` (미노출)
6. `RankingSnapshot(section=, position=, total_results=)` 생성 → `storage.insert_snapshot(...)`
7. 선택적으로 SERP HTML 을 Supabase Storage 에 보관 (재현·검증용)
**출력**: `RankingSnapshot` Pydantic 모델

**핵심 설계 — 도메인 격리**:
- `domain/ranking/tracker.py` 와 `domain/ranking/serp_parser.py` 는 `domain/crawler/*` 를 **직접 import 하지 않는다**.
- `find_position` 시그니처는 `serp_fetcher: Callable[[str], str]` 로 fetcher 만 주입. 파싱은 `domain/ranking/serp_parser` 내부에서 수행 (같은 도메인 모듈).
- URL builder + fetcher 의 합성은 **application/ranking_orchestrator.py** 가 책임.
- 정규식·노이즈 클래스 등은 `serp_parser.py` 에 단일 출처화.

**검증 — 실측 fixture 14건** (`tests/fixtures/integrated_serp/*.html`):
- 노출 9건 — 매칭된 섹션·순위가 모두 실측과 일치 (인기글 4위, 인플루언서 1~5위, VIEW 2~3위 등)
- 미노출 5건 — 어느 섹션에서도 발견되지 않음
- regression 테스트: `tests/test_ranking/test_serp_parser.py`

### [수집-스케줄] check_all_active_rankings

**입력**: `reporter: ProgressReporter | None`
**처리**:
1. 모든 publications 순회 (페이지네이션 batch=100)
2. publication 당 `check_rankings_for_publication` 호출
3. Bright Data rate 보호 위해 publication 간 1초 sleep
4. 개별 실패는 logging.warning 후 다음으로 (배치 전체 중단 X)
**출력**: `RankingCheckSummary` (checked_count, found_count, errors_count, duration_seconds)

#### 발화 경로 — 외부 cron(GitHub Actions) 정식, in-process APScheduler default off

**2026-05-03 변경 — 외부 cron 으로 전환**.

| 경로 | 상태 | 용도 |
|---|---|---|
| GitHub Actions `ranking-cron.yml` → `POST /api/rankings/check-all` | **정식** | 운영 — 매일 09:00 KST(=00:00 UTC) |
| `application/scheduler.py` (in-process APScheduler) | **default off** | 로컬 개발 (`RANKING_SCHEDULER_ENABLED=true`) |

**왜 외부 cron 이 정식인가** — in-process APScheduler 는 Render Starter 컨테이너 재시작/OOM 으로 cron tick 이 누락된다. 2026-04-30·05-01 두 날 ranking_snapshots row 0건 사고 (다른 날은 정상) 로 실측 확인. APScheduler 의 in-memory jobstore 는 재시작마다 초기화되어 `coalesce=True` 의 missed-run replay 도 못 받는다. 외부 cron 은 우리 컨테이너 lifecycle 과 완전 독립이라 누락 불가능 + 실패 시 GitHub UI 에 빨간불·이슈 자동 생성으로 silent failure 차단.

**`POST /api/rankings/check-all` 동작**:
- `X-API-Key` 인증 (`require_api_key`)
- BackgroundTasks 로 비동기 실행, 즉시 `202 {"status":"accepted","started_at":...}` 응답
- 동시 실행 가드: in-memory `threading.Lock` — 이전 배치가 끌리는 동안 중복 호출은 `409`
- 종료 후 `finally` 로 lock 해제 — orchestrator 가 raise 해도 다음 호출 가능

**GitHub Actions workflow 안전장치**:
- `--retry 3 --retry-delay 60 --retry-all-errors` — Render cold start / 일시적 503 흡수
- `concurrency: ranking-daily-check` — 동시 실행 차단
- 실패 시 GitHub Issue 자동 생성 (label: `incident, ranking-cron`)

**운영자 setup 필수**:
- GitHub repo Settings → Secrets → `API_BASE_URL`, `ADMIN_API_KEY` 등록
- 두 secret 모두 비어 있으면 workflow 가 명시적 실패 (`Validate secrets` 단계)

#### 자동 검증 + silent failure 차단 (2026-05-03 보강)

**왜 필요한가** — 2026-05-02 측정 사이클에서 ranking_snapshots 48 건은 정상이나 같은 사이클 api_usage 0 건이었던 사고. dashboard 가 5/2 통째 누락으로 보였고, 사후 분석 전엔 발견 자체가 안 됨.

**구조**:
1. `POST /api/rankings/check-all` 즉시 202 + BackgroundTasks 실행
2. orchestrator 내부:
   - `save_usage_to_supabase` 가 tenacity 1s/2s/4s 3 시도 후에도 실패하면 `RankingCheckSummary.usage_save_failed_count` 에 누적
   - 종료 시 `_last_check_all_result` 모듈 dict 에 `{status, checked_count, found_count, errors_count, usage_save_failed_count, started_at, finished_at}` 저장
3. `GET /api/rankings/check-all/last` 가 그 결과 반환
4. workflow 의 `Verify execution result` step:
   - 15 초 간격, 최대 100 회 polling
   - status='succeeded' + errors_count==0 + usage_save_failed_count==0 → 그린
   - 어느 하나라도 어긋나거나 timeout → fail
5. 실패 시 `Open issue on failure` step 이 GitHub Issue 자동 생성 (label: `incident, ranking-cron`, 본문에 카운터·응답 본문 포함)

**카운터 의미**:
- `errors_count` — `RankingMatchError`/`ValueError` 등 측정 자체가 실패한 publication 수
- `usage_save_failed_count` — 측정은 정상이지만 api_usage INSERT 가 재시도 후에도 실패한 수 (silent failure 방지)
- 두 카운터는 **분리해서 노출** — 같은 사고도 원인이 다르면 다르게 대응해야 함

### [조회] list/timeline

- `GET /api/publications?keyword=...&limit=50` — 등록 목록
- `GET /api/publications/{id}` — 단건 + 최근 30일 timeline 포함
- `GET /api/rankings/{publication_id}?limit=90` — RankingSnapshot 시계열 (날짜 desc)

---

## 4. Supabase 스키마

```sql
-- URL 등록 (네이버 블로그 포스트, 본 프로젝트 발행본 + 외부 URL 모두 수용)
create table publications (
  id uuid primary key default uuid_generate_v4(),
  job_id text,                     -- 어느 job 의 결과물인지 (선택, 추적용)
  keyword text not null,           -- 추적 검색어
  slug text,                       -- output 디렉터리 매칭용 (외부 URL 이면 NULL)
  url text not null unique,        -- 추적 URL (정규화된 형태)
  published_at timestamptz,        -- 발행 시점 (선택, 기본 created_at)
  created_at timestamptz default now()
);

create index publications_keyword_idx on publications(keyword);
create index publications_slug_idx on publications(slug);

-- 순위 스냅샷 (시계열, append-only)
create table ranking_snapshots (
  id uuid primary key default uuid_generate_v4(),
  publication_id uuid not null references publications(id) on delete cascade,
  position int,                    -- 1~100, NULL 이면 100위 밖
  total_results int,               -- SERP 결과 총 개수 (분모, 디버깅용)
  captured_at timestamptz default now(),
  serp_html_path text              -- Supabase Storage 경로 (재현용, NULL 가능)
);

create index ranking_snapshots_publication_idx
  on ranking_snapshots(publication_id, captured_at desc);
```

**롤백 SQL** (배포 실패 시):
```sql
drop table if exists ranking_snapshots;
drop table if exists publications;
```

**기존 schema.sql 영향**: 신규 추가 only. 기존 테이블/뷰 변경 없음.

---

## 5. 기술 스택 & 모델

- **신규 의존성**: `apscheduler>=3.10` (AsyncIOScheduler) — `pyproject.toml` 추가
- **재사용 자산**:
  - Supabase: `config/supabase.py` 의 `get_client()` (이미 존재)
  - Bright Data Web Unlocker: `domain/crawler/serp_collector.py`
  - FastAPI 인증 미들웨어: 기존 `require_api_key` (X-API-Key)
  - Next.js 인증 패턴: 기존 `useApi` 훅 (UsageDashboard 직접 origin 호출 패턴 참조)
- **LLM 호출 0건** — 순위 추적은 결정적 매칭이라 LLM 불필요. **비용 효율 매우 높음**

---

## 6. 디렉토리 구조 (신규/변경)

```
domain/
└── ranking/                          # 신규 도메인
    ├── __init__.py
    ├── model.py                      # Publication, RankingSnapshot, RankingTimeline
    ├── url_match.py                  # BLOG_POST_URL_RE (의도적 복제), normalize, urls_match
    ├── tracker.py                    # find_position (DI 패턴, crawler import X)
    ├── storage.py                    # Supabase CRUD
    └── CLAUDE.md                     # 도메인 규칙 (DI, 정규식 복제, 30/300줄)

application/
├── ranking_orchestrator.py           # 신규: register/check/check_all
└── scheduler.py                      # 신규: AsyncIOScheduler 래퍼

web/api/routers/
└── rankings.py                       # 신규: 5개 엔드포인트

scripts/
├── register_publication.py           # 신규
└── check_rankings.py                 # 신규

web/frontend/src/
├── components/
│   ├── PublicationForm.tsx           # 신규: URL 등록 폼
│   └── RankingTimeline.tsx           # 신규: 시계열 표
└── app/
    ├── results/[slug]/page.tsx       # 수정: 위 컴포넌트 통합
    └── rankings/page.tsx             # 신규: 통합 대시보드

tests/
├── test_ranking/                     # 신규: 5 파일
├── test_application/
│   ├── test_ranking_orchestrator.py  # 신규
│   └── test_scheduler.py             # 신규
└── test_web/
    └── test_rankings_api.py          # 신규

config/
└── schema.sql                        # 수정: 2 테이블 추가
```

---

## 7. 실행 방법

```bash
# 본 프로젝트로 발행한 글 등록 (slug 로 결과 페이지와 연결)
python scripts/register_publication.py \
  --keyword "신사 다이어트 한의원" \
  --slug "신사다이어트한의원" \
  --url "https://blog.naver.com/myblog/123456789" \
  --published-at "2026-04-24"

# 외부 URL 등록 (slug 생략 — 결과 페이지 매칭 없이 순위만 추적)
python scripts/register_publication.py \
  --keyword "신사 다이어트 한의원" \
  --url "https://blog.naver.com/competitor/987654321"

# 단일 publication 즉시 체크
python scripts/check_rankings.py --publication-id <uuid>

# 전체 즉시 체크 (수동 트리거)
python scripts/check_rankings.py --all

# 자동 수집은 백엔드 lifespan 에서 APScheduler 가 매일 09:00 KST 실행
# 비활성화: RANKING_SCHEDULER_ENABLED=false (테스트·디버깅용)
```

---

## 8. 개발 순서

`tasks/todo.md` Ranking Tracker MVP 섹션의 R1.1 → R7 순.

요약:
- **R1** 도메인 + Supabase (6h)
- **R2** Application + 스케줄러 (4h)
- **R3** API + lifespan (3h)
- **R4** CLI (1.5h)
- **R5** Web UI (4h)
- **R6** 통합 회귀 (1.5h)
- **R7** 검증 + 커밋 (0.5h)

**총 ~20.5h, 단일 PR.**

---

## 9. 검증 기준

- `bash .claude/hooks/build-check.sh` 그린 (ruff/format/architecture/mypy/pytest 0 에러)
- 기존 371개 테스트 모두 통과 + ranking 신규 테스트 ≥ 25개
- `architecture-check.sh` 가 `domain/ranking → domain/crawler` 직접 import 차단 (DI 패턴 강제)
- Supabase 마이그레이션 후 `select count(*) from publications/ranking_snapshots` 둘 다 0
- 매일 스케줄러가 09:00 KST cron 으로 등록되는지 단위 테스트 검증

---

## 10. 핵심 설계 원칙

1. **도메인 격리 절대 준수** — `domain/ranking → domain/crawler` import 금지. DI 패턴으로 격리.
2. **URL 정규화 단일 출처** — `url_match.py` 만이 정규화 책임. 다른 모듈은 호출만.
3. **스냅샷 append-only** — `ranking_snapshots` 는 update/delete 안 함. 모든 측정은 시계열 누적.
4. **멱등** — 동일 URL 재등록은 기존 publication 반환. 동일 시점 중복 snapshot 은 `captured_at` 으로 자연 분리.
5. **개별 실패는 격리** — `check_all_active_rankings` 의 publication 단위 실패가 배치 전체를 중단시키지 않음.
6. **append-only 스냅샷 → 분석은 별도** — MVP 는 측정만. 학습/순위 예측은 Phase 2.
7. **Bright Data rate 보호** — publication 간 1초 sleep. 다중 publication 동시 처리 X.
8. **단일 인스턴스 전제** — APScheduler in-process. 멀티 인스턴스 전환 시 advisory lock 필수.
9. **모든 도메인 함수 Pydantic 반환** — print/stdout 금지, 30줄/300줄 한계 준수.
10. **테스트 격리** — Bright Data·Supabase 모두 mock. 실 호출 테스트는 별도 실측 단계.

---

## 11. 위험 요소

| ID | 내용 | 완화 |
|---|---|---|
| R1 | `BLOG_POST_URL_RE` 정규식이 ranking/serp_collector 양쪽에 복제됨 → 동기화 누락 | lessons.md 에 "serp_collector 정규식 변경 시 url_match.py 동시 갱신" 패턴 명시 + url_match.py 주석 |
| R2 | Supabase 마이그레이션 실패 시 부분 적용 가능 | 롤백 SQL 명세(§4) + 트랜잭션 단위 적용 권고 (대시보드 SQL Editor 에서 BEGIN/COMMIT) |
| R3 | APScheduler 가 백엔드 재시작 시 잡 누락/중복 | `coalesce=True, max_instances=1` 설정 + lessons.md 에 멀티 인스턴스 advisory lock 메모 |
| R4 | 매일 모든 publication SERP 체크 → Bright Data 비용 폭주 | publication 당 1초 sleep + 비용 추정: 100 publication × 30일 × $0.01 ≈ **월 $30** (감내 가능) |
| R5 | 사용자가 발행 URL 입력 안 하면 데이터 0 | UI 결과 페이지 상단에 미등록 시 "발행 URL 등록" 강조 배너 |
| R6 | 네이버가 SERP 구조 변경 시 파싱 실패 → 모든 publication NULL | 기존 serp_collector regression 테스트가 1차 방어. 신규 ranking_snapshots 의 NULL 비율 모니터링 |

---

## 12. Phase 2 확장 지점 (MVP 이후)

- 도메인 자동 매칭 (사용자 블로그 도메인 1회 등록 → 발행 URL 입력 자동화)
- 순위 데이터 + 패턴 카드 메타 매칭 학습 → outline 생성 시 가중치 반영
- 키워드 군집화 (유사 의도 키워드 묶음) → 콘텐츠 카니발리제이션 감지
- 모바일/PC SERP 분리 측정
- 클릭률(CTR) 추정 모델 (Naver Search Advisor 연동)

---

## Phase 1 — 미노출 사유 진단 (evidence-based)

### 목적
"왜 안 뜨는가" 를 직접 알 수는 없으나 관측 데이터로 **추정 진단**을 제공하고, 진단별 결과를 누적해 추후 통계화한다. 핵심 원칙은 "확정 단언이 아니라 근거 동반 추정".

### 5개 룰 (P1)

| reason | confidence | 근거 |
|---|---|---|
| `no_publication` | 1.0 | publications.url 비어있음 (결정적) |
| `no_measurement` | 1.0 | snapshot 0건 (결정적) |
| `lost_visibility` | 0.6~0.9 | 과거 노출 + 최근 N일 연속 null. streak 길이에 비례 |
| `never_indexed` | 0.5~0.85 | 발행 D+3 이상 + 한 번도 미발견. 경과일에 비례 |
| `cannibalization` | 0.9 | Top10 안에 같은 author 의 다른 URL 노출 (URL 매칭 강신호) |

### 데이터 모델

```sql
-- 매 측정마다 SERP Top10 전체 보존 (카니발 감지·SOV 분석 기반)
serp_top10_snapshots (id, keyword, captured_at, rank, url, section, blog_id, is_ours)

-- 진단 결과 + 결과 추적 + 사용자 액션
diagnoses (
  id, publication_id, diagnosed_at,
  reason, confidence, evidence (jsonb), metrics (jsonb), recommended_action,
  outcome_checked_at, re_exposed, re_exposed_at, re_exposed_section, re_exposed_position,
  republished, republished_at, republish_publication_id,
  user_action, user_action_at
)
```

### 동작 흐름
1. 매일 09:00 KST `check_all_active_rankings` 가 publication 측정
2. 측정 후 `_build_top10_from_html` 이 SERP HTML 의 Top10 을 `serp_top10_snapshots` 에 보관
3. `diagnose_publication` 자동 호출 → 5개 룰 평가 → 진단 저장 (실패해도 측정 자체는 유지)
4. 사용자는 `/rankings/{id}` 에서 진단 카드 확인 → 액션 버튼(재발행/보류/기각/경쟁 인정) 선택
5. 다음 측정 사이클이 outcome 컬럼을 갱신해 진단 정확도 자체 검증

### 후속 추적 (장기 데이터 누적)
- 진단별 재노출률 / 평균 회복 일수
- 사용자 액션 vs 시스템 진단 일치율
- 재발행 후 D+7 노출 성공률 vs 자연 노출률 (control group 비교)

이 통계가 누적되면 "진단의 신뢰도" 자체를 데이터로 입증 가능. 6개월~1년 운영 후 분석 대시보드 별도 설계.

### API
- `GET /rankings/publications/{id}/diagnoses` — 진단 시계열
- `POST /rankings/publications/{id}/diagnose` — 즉시 실행
- `POST /rankings/diagnoses/{id}/action` — 사용자 액션 기록 (legacy 단건)
- `GET /rankings/diagnoses/board` — 조치 필요 publication + 최신 진단 보드 (`/insights` '진단 조치' 탭)
- `POST /rankings/diagnoses/bulk-action` — 진단 ID 일괄 액션 (4종)

### 진단 보드 일괄 액션 (Phase 1 후속, 2026-05-15)

`/insights` '진단 조치' 탭 — `workflow_status="action_required"` publication 의 최신 진단을 confidence·reason 으로 필터해 4종 액션(`republished` / `held` / `dismissed` / `marked_competitor_strong`)을 일괄 처리.

**액션 라우팅** (`application/diagnosis_board_orchestrator.py`):
- `republished` → `republish_orchestrator.start_republish` (draft + pipeline job 생성, undo 불가)
- `held` → `publication_actions_orchestrator.hold(days=7)` (자동 큐 복귀)
- `dismissed` → `publication_actions_orchestrator.dismiss` (추적 제외, 복원 가능)
- `marked_competitor_strong` → `visibility_diagnoses.user_action` 기록만 (publication 상태 변경 X)

**안전 정책**:
- 실행 시점에 publication.workflow_status 재검증 — `action_required` 아니면 `skipped: stale workflow_status`
- `held` / `dismissed` 가 이미 같은 상태면 `skipped`
- `republished` 의 RuntimeError 는 메시지 분류 — "active" 포함 시 `skipped`, 그 외 `failed`
- 5건 이상 일괄 재발행은 frontend 가 typed confirmation (`REPUBLISH` 입력) 강제
- 응답: `{ total, succeeded[], skipped[], failed[] }` partial failure 데이터화

**단일 출처** (drift 차단):
- backend `domain/diagnosis/model.py` 의 `UserAction` Literal ↔ frontend `lib/labels.ts` 의 `DIAGNOSIS_ACTION_KEYS` 일치 회귀 테스트 (`tests/test_application/test_diagnosis_board_orchestrator.py::TestSingleSourceOfTruth`)

### 도메인 격리
- `domain/diagnosis/` 는 `domain.ranking` Pydantic 모델만 입력으로 받음
- SERP fetch / storage 호출 없음 — 룰 함수는 순수 계산
- 작성자 식별 헬퍼는 `domain/ranking/url_match.author_key` 와 의도적 복제 (격리 유지)

## 변경 이력

- `2026-04-24`: v1 초안. R1~R7 작업 plan 동기화. 단일 인스턴스 전제, DI 도메인 격리, append-only 스냅샷, 매일 09:00 KST 자동 수집.
- `2026-04-24`: `publications.slug` nullable 화. 외부 URL(직접 발행 안 한 글) 도 같은 등록·체크·시계열 흐름으로 추적 가능. `/rankings` 대시보드에 외부 URL 등록 폼 추가.
- `2026-04-27`: **섹션 기반 측정으로 전환**. 통합검색 메인 페이지(`?where=nexearch`) 를 받아 섹션별(인플루언서·VIEW·인기글·뉴스 등)로 분리해 매칭. `RankingSnapshot.section` 컬럼 추가, `register_publication` URL 검증 완화(카페·외부 사이트 허용). 실측 14건 기반 regression 테스트 추가.
- `2026-04-27`: **Phase 1 미노출 사유 진단** 추가. 5개 룰(`no_publication` / `no_measurement` / `lost_visibility` / `never_indexed` / `cannibalization`)로 evidence-based 진단. `serp_top10_snapshots` · `diagnoses` 신규 테이블. 측정 사이클이 자동 트리거. `/rankings/{id}` 에 진단 카드 + 사용자 액션 버튼.
- `2026-05-03`: **외부 cron 전환**. in-process APScheduler 가 Render Starter 컨테이너 재시작·OOM 으로 4/30·5/1 cron tick 을 누락한 사고 (ranking_snapshots row 0건 vs 인접 날 100여건) 후속. `POST /api/rankings/check-all` 신규 + `.github/workflows/ranking-cron.yml` 매일 09:00 KST 발화. APScheduler 는 `RANKING_SCHEDULER_ENABLED=true` 로 로컬 개발에서만 켤 수 있게 default off. `web/api/main.py` 에 `logging.basicConfig(INFO)` 추가 — uvicorn 이 root logger 를 WARNING 으로 두는 바람에 cron tick · lifespan 시작 로그가 silent 였던 부수 사고도 동시 해결.
- `2026-05-03`: **silent failure 차단**. 2026-05-02 측정 사이클에서 ranking_snapshots 48 건 정상 + 같은 사이클 api_usage 0 건이었던 사고 후속. `save_usage_to_supabase` 에 tenacity retry (1s/2s/4s, 3 시도) + ERROR 로그 강화 (`row_count` + `exc_type` + `first_row_provider/keyword`). `RankingCheckSummary.usage_save_failed_count` 신규 필드. `GET /api/rankings/check-all/last` 폴링 endpoint 와 GitHub Actions workflow 의 `Verify execution result` step 추가 — 어느 카운터든 0 보다 크면 workflow fail + Issue 자동 생성으로 silent failure 영구 차단.
- `2026-05-06`: UX Refactor 결과 반영. **백엔드 무변경** (모든 `/api/rankings/*` endpoint 그대로). frontend 라우트 변경 — `/rankings` 가 `/` (운영 홈) 로 영구 redirect (운영 OS 메인 진입점 승격). `/rankings/[id]` (publication 상세) 는 그대로 유지 (외부 SEO 인입). PublicationActionRow 정보밀도 정리 — 9~14요소 → 4요소 + Primary CTA + ⋯ Dropdown (UX P3). PublicationForm `variant=create|edit` 통합 — 기존 ExternalUrlForm + PublicationEditDialog 흡수 (UX P5). 라우트 단일 출처: `docs/ROUTES.md`
- `2026-05-15`: **진단 보드 일괄 액션** 추가. `/insights` '진단 조치' 탭에서 `workflow_status=action_required` publication 의 최신 진단을 confidence·reason 으로 필터해 4종 액션 일괄 처리. `application/diagnosis_board_orchestrator.py` 신설 — action 별로 다른 orchestrator 라우팅 (republish / publication_actions / user_action 기록). 안전 정책: 실행 시점 workflow_status 재검증으로 stale 차단, `republished` RuntimeError 는 "active" 메시지만 skipped (나머지 failed), 5건 이상 재발행은 typed confirmation (`REPUBLISH` 입력) 강제. 응답은 `succeeded[] / skipped[] / failed[]` 분리로 partial failure 데이터화. backend `UserAction` Literal ↔ frontend `DIAGNOSIS_ACTION_KEYS` cross-check 회귀 테스트로 drift 차단. codex CLI 와 plan/code 두 단계 review 협업.
