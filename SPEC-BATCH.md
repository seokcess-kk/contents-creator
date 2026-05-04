# 키워드 배치 운영 시스템 (Batch Pipeline) — Spec v1

본 문서는 contents-creator 의 **대량 키워드 운영 MVP** 명세다.
SEO 트랙(SPEC-SEO-TEXT.md)·브랜드 카드 트랙(SPEC-BRAND-CARD.md)·순위 추적(SPEC-RANKING.md)과 **병행되는 운영 보조 트랙**이며, 의존 방향은 단방향(batch → 단일 orchestrator 호출만).

작성: 2026-05-04
연관: tasks/todo.md "Batch Pipeline MVP" 섹션, application/CLAUDE.md, SPEC-SEO-TEXT.md §12

---

## 1. 목적

100개 이상의 키워드를 단건 CLI/웹 호출로 처리하던 한계를 넘어, **CSV 한 번 업로드로 분석·생성·검수까지 자동화**한다.

- 사용자 조작 공수 95% 절감 (100건 클릭 → 1회 업로드)
- 사전 필터로 무가치 키워드 자동 스킵 (100→30~50로 압축, Phase 2)
- 같은 토픽의 중복 작성 방지 (cluster 단위 PatternCard 재사용, Phase 2)
- 야간 LLM 비용 절감 (Anthropic Batch API adapter, Phase 3)
- 검수 부담 자동화 (위반·미달만 알림, Phase 4)

**명시 비목표** (오늘 plan 기준):

- **단일 흐름 변경 0** — 기존 `scripts/run_pipeline.py`, `POST /api/jobs`, `application/orchestrator.py` 4 함수는 그대로 동작
- **자동 클러스터링 X** — MVP 는 사용자 입력 `cluster_id` 만. 자동화는 데이터 누적 후 Phase 5+
- **멀티 인스턴스 worker X** — 단일 web process 전제. 멀티 worker/Redis 는 Phase 3+
- **자동 발행 강제 X** — 검수 통과 후 사용자 승인 → publications 등록 (Phase 4 의 자동화도 opt-in)

---

## 2. 핵심 원칙 (불변)

1. **단일 흐름 100% 보존** — `application/orchestrator.py` 4 함수 시그니처 불변, 기존 CLI/웹 API 무수정 (additive only)
2. **Dual-mode** — `now`(일반 API) / `overnight`(Anthropic Batch API) / `auto`(priority 기반 라우팅). **Phase 1 은 `now` 만 처리**, `overnight`·`auto` 는 DB/API 받되 `400 Not Supported Yet`
3. **자원 격리** — `JobManager`(단일 전용) ↔ `BatchJobManager`(배치 전용) 분리. BrightData 동시성은 단일 프로세스 semaphore (Phase 1 안전망 한정 — 멀티 워커 진입 시 Redis advisory lock 필요)
4. **수동 우선** — 클러스터링은 사용자 입력 `cluster_id` + `cluster_role` 부터. 자동 클러스터링은 운영 데이터 누적 후
5. **UI default = `analyze`** — 100개 full pipeline 실수 차단. `pipeline` 은 명시 선택만 가능
6. **PatternCard 모델 무수정** — 재사용은 `keyword_batch_items.pattern_card_id` 로만 표현. `PatternCard.schema_version` 은 그대로 `2.0`
7. **FK 컬럼 nullable** — Phase 1 은 caller 가 DB id 를 회수 못 함 (`save_pattern_card → Path`, `generated_contents.insert` fire-and-forget). `(job_id, slug, keyword)` triple 로 link. id 회수 보강은 Phase 2

---

## 3. 단계별 파이프라인

### Phase 1 (3~4일) — 배치 인프라 + operation 분기 + retry + dashboard

**입력**: CSV 파일 (또는 웹 textarea)

**CSV 스키마**:
```csv
keyword,operation,priority,cluster_id,cluster_role,intent,region,brand_id,target_url,memo
천안다이어트한의원,analyze,1,cluster-cn-diet,primary,info,천안,,,첫 분석 대상
천안 다이어트 한약,analyze,3,cluster-cn-diet,member,info,천안,,,
천안 비만 한의원,pipeline,2,cluster-cn-obesity,primary,info,천안,,blog.naver.com/x/123,
```

| 컬럼 | 필수 | 의미 | 처리 |
|---|---|---|---|
| keyword | ✅ | 분석/생성 대상 | 그대로 |
| operation | ❌ | `analyze` / `generate` / `pipeline` | default = `analyze` |
| priority | ❌ | 1=highest, 9=lowest | default = 5. Phase 3 dual-mode 라우팅 시 사용 |
| cluster_id | ❌ | 같은 토픽 그룹 식별자 | Phase 1 은 컬럼만 저장, Phase 2 활성화 |
| cluster_role | ❌ | `primary` / `member` | default = `member`. Phase 2 활성화 |
| intent / region / brand_id / target_url / memo | ❌ | 운영 메타 | 운영자 검수 큐 표시용 |

**처리 흐름** (Phase 1 단순):
1. CSV upload → `keyword_batches` 1 row + `keyword_batch_items` N row insert
2. `BatchJobManager` worker N개로 dequeue
3. item 단위로 `application.orchestrator.run_analyze_only/run_generate_only/run_pipeline` 호출 (operation 분기)
4. retry_count 누적, max_retries(default 2) 초과 시 `failed`
5. WebSocket 또는 poll 로 dashboard 갱신

**상태 머신** (Phase 1 단순):
```
queued → running → succeeded / needs_review / failed
                ↘ skipped (사전 필터 — Phase 2 활성)
```
※ `analyzing → ready_to_generate → generating` 등 세부 상태는 Phase 2 에서 활성화 (지금 두면 dead state)

**API**:
- `POST /api/batches` — multipart CSV 또는 JSON. `mode=now` 만 200, 그 외 400
- `GET /api/batches?limit=20` — 목록
- `GET /api/batches/{id}` — 단건 + 진행 요약
- `GET /api/batches/{id}/items?status=...` — item 페이지네이션
- `POST /api/batches/{id}/cancel` — 진행 중 batch 중단 (남은 queued item 만 cancelled)
- `POST /api/batches/{id}/items/{item_id}/retry` — 단건 재시도

**CLI**:
```bash
python scripts/run_batch.py --csv keywords.csv --mode now --max-workers 2
python scripts/run_batch.py --status <batch_id>
```

**자원 격리**:
- `BatchJobManager(MAX_WORKERS=2~3)` — env `BATCH_MAX_WORKERS` 로 조정
- `domain/crawler/brightdata_client.py` 에 module-level `threading.Semaphore(N)` — env `BRIGHTDATA_CONCURRENT_LIMIT` (default 5)
- 단일 프로세스 한정 보호. 멀티 워커/인스턴스 진입 시 Redis advisory lock 으로 교체 (Phase 3+)

---

### Phase 2 (3~4일) — 사전 필터 + cluster 재사용 + 검수 큐

**가치**: 100→30~50 압축 + 검수 효율 5~10배

**사전 필터** (analyze 결과로 자동 분류):
- `min_search_volume` (batch 단위, default None — 임계값 미설정 시 호출 0) — 검색량 미달 → `skipped`
- `max_difficulty` (batch 단위, default None) — 난이도 초과 → `skipped`
- `cluster_dedupe` (default **False** — PR2 보수 결정) — 명시적 ON 시만 같은 cluster 재사용 활성

**Cluster 재사용**:
1. `cluster_role=primary` 만 분석 → PatternCard 생성 → `keyword_batch_items.pattern_card_id` 저장
2. 같은 cluster 의 `member` 들은 primary 의 `pattern_card_id` 그대로 참조
3. `cluster_role` 미지정 시 폴백: 같은 cluster 안에서 `priority` 최상위 = primary
4. `PatternCard` 모델은 무수정 (재사용 관계는 batch_item 쪽 컬럼만)

**클러스터 재사용 사용 가이드** (PR2 추가):

cluster 재사용은 **검색 의도가 사실상 같은 long-tail 변형 묶음**에만 사용한다. PatternCard 재사용 자체는 분석 결과 (target_reader, sections, DIA+, distributions) 만 공유하고 outline + body 는 키워드별로 새로 생성하지만, cluster 의 키워드들이 검색 의도가 너무 가까우면 outline·body 도 비슷해질 가능성이 잔존한다. 본문 유사도가 높아지면 네이버 SERP 에서 두 키워드 모두 1페이지 노출이 어려워진다 (duplicate content penalty). 따라서:

- **권장 묶음**: 같은 의도의 long-tail 변형 — `다이어트 한의원 추천` ↔ `좋은 다이어트 한의원`
- **분리 묶음**: 지역·브랜드·intent 가 다른 키워드 — `강남 다이어트 한의원` 과 `역삼 다이어트 한의원` 은 같은 cluster 로 묶지 말 것
- **default OFF** 정책: 의도하지 않은 cluster 재사용으로 인한 노출 페널티를 차단. 운영자가 키워드 묶음을 검토 후 명시적으로 `--cluster-dedupe` (CLI) / checkbox ON (Web) / `cluster_dedupe=true` (API) 로 켤 때만 활성

본문 차별화 자동 검증 (Jaccard 유사도 측정 후 needs_review 마킹) 과 outline negative example 주입은 PR3 검수 큐와 함께 추가 예정.

**상태 머신 활성화** (Phase 2):
```
queued → analyzing → ready_to_generate → generating → needs_review → published / failed
                  ↘ skipped (사전 필터)
```

**FK 정합성 보강**:
- `application/models.py:GenerateResult` 에 `generated_content_id: str | None`, `pattern_card_id: str | None` 필드 추가
- `application/stage_runner.py:914` 의 `client.table("generated_contents").insert(...)` 가 `.execute().data[0]["id"]` 회수해 caller 까지 전달
- `domain/analysis/pattern_card.py:save_pattern_card` 가 DB id 까지 반환하도록 보강 (또는 별도 `get_latest_pattern_card_id(keyword)` helper)
- Phase 1 의 `(job_id, slug, keyword)` triple link 는 호환성 위해 유지

**검수 큐** (`/batches/{id}/review`):
- 키워드 / 난이도 등급 / 검색량 / 의료법 통과 / 이미지 생성 / 우선순위 / publication link
- 일괄 액션: 발행 승인, 재생성, 보류, 기각
- 필터: `review_status=pending` 만 default 표시

---

### Phase 3 (3~4일) — Anthropic Batch API adapter (LLM 독립 호출 한정) + worker process 분리

**중요** — Anthropic Batch API 는 **pipeline 전체를 대체하지 않는다**. BrightData 크롤링·Gemini 이미지·Supabase 저장·compliance flow 는 일반 흐름 유지. **LLM 독립 호출 구간만** Batch API 로 라우팅.

**Batch API 적용 대상** (의존 없는 단발 LLM 호출):
- 분석 단계 [4a]/[4b] 카드 추출 (키워드 N개 동시 batch 가능)
- 의료법 검증 단일 프롬프트 (compliance/checker.py)
- 톤·품질 평가 같은 후처리 단발 호출
- 적용 시 **약 -30~40% 비용** (전체 pipeline 의 일부만 batch)

**Batch API 적용 제외** (의존 체인):
- outline → body → compliance/fix 순차 의존 — 한 번에 batch 못 함
- 스트리밍이 필요한 인터랙티브 호출
- 이 구간은 `mode="overnight"` 여도 **일반 API 그대로**

**Dual-mode 라우팅** (Phase 3 활성화):
```python
# batch_router.py 에서 mode + priority 기반
if item.mode == "now" or (item.mode == "auto" and item.priority <= 3):
    enqueue_immediate(item)              # 일반 API 큐
elif item.mode == "overnight" or (item.mode == "auto" and item.priority >= 4):
    enqueue_overnight_with_batch_api(item)  # 야간 worker + LLM 독립 호출만 batch API
```

**Worker process 분리**:
- Phase 1~2 의 `BatchJobManager` 는 web process in-memory MVP
- Phase 3 부터 별도 worker process 또는 Render cron command 로 분리
  - 이유: deploy/restart 시 in-memory state 손실 + web process 응답성 보호
  - 학습 적용: 2026-05-02 in-process APScheduler 사고와 같은 패턴 회피
- 야간 시작 시간 (default 22:00 KST) 에 `mode="overnight" + status="queued"` 일괄 처리

**멀티 워커 진입 시 자원 보호**:
- BrightData 단일 프로세스 semaphore 가 한계 도달 → Redis 또는 Supabase advisory lock 으로 전역 한도 강제
- 그 전엔 단일 worker 권장

---

### Phase 4 (2~3일) — 알림 + publication 자동 등록

**알림 채널** (env 미설정 시 스킵):
- `SLACK_WEBHOOK_URL` (권장)
- 또는 이메일 (Resend, SendGrid)

**알림 트리거**:
- 배치 완료 — 요약 (succeeded N / failed M / skipped K / cost $X)
- 의료법 위반 발견 — 키워드 + 위반 카테고리
- 배치 전체 실패 — 즉시 알림
- 야간 batch 시작/종료

**publication 자동 등록** (opt-in):
- `target_url` 컬럼 채워진 item + 검수 통과 (`compliance_passed=true` + `quality_score >= AUTO_PUBLISH_THRESHOLD`) → `publications` 테이블 자동 INSERT
- → `/rankings` 추적 사이클 자동 진입
- env 미설정 시 비활성화 (사용자가 검수 큐에서 수동 발행 등록만 가능)

---

## 4. Supabase 스키마

```sql
-- 배치 메타
create table keyword_batches (
  id uuid primary key default uuid_generate_v4(),
  name text,
  mode text not null default 'now',          -- 'now' | 'overnight' | 'auto' (Phase 1 은 now 만)
  status text not null default 'queued',     -- queued/running/completed/failed/cancelled
  total_count int not null,
  succeeded_count int default 0,
  failed_count int default 0,
  skipped_count int default 0,
  needs_review_count int default 0,
  estimated_cost_usd numeric default 0,
  -- 사전 필터 임계값 (Phase 2 활성)
  min_search_volume int,
  max_difficulty text,
  cluster_dedupe boolean default true,
  -- Phase 4 자동 발행
  auto_publish_enabled boolean default false,
  created_at timestamptz default now(),
  started_at timestamptz,
  completed_at timestamptz
);

-- 배치 item
create table keyword_batch_items (
  id uuid primary key default uuid_generate_v4(),
  batch_id uuid not null references keyword_batches(id) on delete cascade,

  -- 입력 (CSV)
  keyword text not null,
  operation text not null default 'analyze', -- 'analyze' | 'generate' | 'pipeline'
  mode text not null default 'now',          -- batch.mode 상속 또는 item override
  priority int default 5,
  cluster_id text,
  cluster_role text default 'member',        -- 'primary' | 'member'
  intent text,
  region text,
  brand_id uuid references brand_profiles(id),
  target_url text,
  memo text,

  -- 실행 메타
  status text not null default 'queued',
  -- queued/running/succeeded/needs_review/failed/skipped
  -- (Phase 2: analyzing/ready_to_generate/generating 활성)
  retry_count int not null default 0,
  max_retries int not null default 2,
  job_id text,                               -- 단일 job 추적 (Phase 1 link 키)
  error text,
  estimated_cost_usd numeric default 0,

  -- 분석 결과 (Phase 2 에서 채워짐, nullable)
  search_volume int,
  difficulty_grade text,                     -- LOW / MEDIUM / HIGH / MISSING

  -- 생성 결과 (nullable)
  pattern_card_id uuid references pattern_cards(id),
  generated_content_id uuid references generated_contents(id),
  quality_score numeric,
  compliance_passed boolean,

  -- 검수 (Phase 2)
  review_status text default 'pending',      -- pending / approved / rejected / needs_fix
  reviewer text,
  reviewed_at timestamptz,

  -- 발행 (Phase 4)
  publication_id uuid references publications(id),
  published_at timestamptz,

  -- 시점
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);

create index keyword_batch_items_batch_idx on keyword_batch_items(batch_id);
create index keyword_batch_items_status_idx on keyword_batch_items(status);
create index keyword_batch_items_review_idx on keyword_batch_items(review_status);
create index keyword_batch_items_cluster_idx on keyword_batch_items(batch_id, cluster_id);
```

**롤백 SQL**:
```sql
drop table if exists keyword_batch_items;
drop table if exists keyword_batches;
```

**FK nullable 원칙**: `pattern_card_id`, `generated_content_id`, `publication_id`, `brand_id` 모두 nullable. Phase 1 에서 못 채워도 상태 진행 막지 않음. Phase 2 의 보강 PR 이 FK 회수 책임.

---

## 5. 데이터 모델 (Pydantic)

```python
# domain/batch/model.py (신규 도메인)
class KeywordBatch(BaseModel):
    id: str | None = None
    name: str | None = None
    mode: Literal["now", "overnight", "auto"] = "now"
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    total_count: int
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    needs_review_count: int = 0
    estimated_cost_usd: float = 0
    min_search_volume: int | None = None
    max_difficulty: str | None = None
    cluster_dedupe: bool = True
    auto_publish_enabled: bool = False
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class KeywordBatchItem(BaseModel):
    id: str | None = None
    batch_id: str
    keyword: str
    operation: Literal["analyze", "generate", "pipeline"] = "analyze"
    mode: Literal["now", "overnight", "auto"] = "now"
    priority: int = 5
    cluster_id: str | None = None
    cluster_role: Literal["primary", "member"] = "member"
    intent: str | None = None
    region: str | None = None
    brand_id: str | None = None
    target_url: str | None = None
    memo: str | None = None

    status: str = "queued"
    retry_count: int = 0
    max_retries: int = 2
    job_id: str | None = None
    error: str | None = None
    estimated_cost_usd: float = 0

    search_volume: int | None = None
    difficulty_grade: str | None = None
    pattern_card_id: str | None = None
    generated_content_id: str | None = None
    quality_score: float | None = None
    compliance_passed: bool | None = None

    review_status: Literal["pending", "approved", "rejected", "needs_fix"] = "pending"
    reviewer: str | None = None
    reviewed_at: datetime | None = None

    publication_id: str | None = None
    published_at: datetime | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class BatchEnqueueResult(BaseModel):
    """CSV upload 결과 — created/skipped/failed 분류."""
    batch_id: str
    total: int
    created: int
    skipped: int          # 키워드 중복·형식 오류
    failed: int
```

---

## 6. 디렉터리 구조 (신규/변경)

```
domain/
└── batch/                            # 신규 격리 도메인 (STAGE_ORDER[batch]=0)
    ├── __init__.py
    ├── model.py                      # KeywordBatch, KeywordBatchItem 등 Pydantic
    ├── csv_parser.py                 # CSV → KeywordBatchItem 리스트 변환 + 검증
    ├── storage.py                    # Supabase CRUD
    └── CLAUDE.md                     # 도메인 규칙

application/
├── batch_orchestrator.py             # 신규: enqueue/dispatch/retry/cancel
└── batch_job_manager.py              # 신규: worker pool (단일 JobManager 와 분리)

web/api/routers/
└── batches.py                        # 신규: 6 엔드포인트

scripts/
└── run_batch.py                      # 신규 CLI

web/frontend/src/
├── app/batches/
│   ├── page.tsx                      # 신규: 배치 목록 + 진행 dashboard
│   ├── [id]/page.tsx                 # 신규: 단건 + item list
│   └── [id]/review/page.tsx          # Phase 2: 검수 큐
└── components/
    ├── BatchUploadForm.tsx           # CSV/textarea
    ├── BatchProgressTable.tsx        # poll 기반 진행률
    └── BatchReviewQueue.tsx          # Phase 2

tests/
├── test_batch/                       # 도메인 (csv_parser, storage)
├── test_application/test_batch_orchestrator.py
├── test_application/test_batch_job_manager.py
└── test_web/test_batches_api.py

config/
└── schema.sql                        # 2 테이블 추가
```

**`domain/batch` 격리 규칙** (CLAUDE.md):
- `domain/batch` → 다른 도메인 import 금지 (격리)
- `application/batch_orchestrator` 가 `domain/batch` + `application.orchestrator` 합성
- `architecture-check.sh` 의 `STAGE_ORDER[batch]=0` 등록

---

## 7. 실행 방법

```bash
# CSV 한 번 업로드 (Phase 1, mode=now 만)
python scripts/run_batch.py \
  --csv keywords.csv \
  --mode now \
  --max-workers 2 \
  --name "2026-Q2 천안 다이어트 캠페인"

# 진행 상태 조회
python scripts/run_batch.py --status <batch_id>

# 단건 재시도 (실패 item)
python scripts/run_batch.py --retry-item <item_id>

# Phase 2~4 (점진 활성)
python scripts/run_batch.py --csv keywords.csv --mode now \
  --min-search-volume 200 --max-difficulty MEDIUM        # Phase 2 사전 필터
python scripts/run_batch.py --csv keywords.csv --mode overnight  # Phase 3
python scripts/run_batch.py --csv keywords.csv --auto-publish    # Phase 4
```

**웹 UI** — `/batches` 페이지에서 동일 기능. CSV 업로드 + 옵션 폼 + dashboard.

**환경변수** (Phase 별 추가):

| Phase | env | 기본값 | 의미 |
|---|---|---|---|
| 1 | `BATCH_MAX_WORKERS` | 2 | 동시 worker 수 |
| 1 | `BRIGHTDATA_CONCURRENT_LIMIT` | 5 | semaphore 한도 |
| 2 | `BATCH_MIN_SEARCH_VOLUME` | 200 | 기본 필터 임계값 |
| 2 | `BATCH_MAX_DIFFICULTY` | MEDIUM | 기본 난이도 상한 |
| 3 | `OVERNIGHT_START_HOUR` | 22 | 야간 worker 시작 시각 (KST) |
| 3 | `BATCH_WORKER_PROCESS` | false | true 면 별도 process 분리 |
| 4 | `SLACK_WEBHOOK_URL` | (none) | 알림 webhook |
| 4 | `AUTO_PUBLISH_THRESHOLD` | 85 | 자동 발행 quality_score 임계값 |

---

## 8. 단일 흐름 보호 — Phase 마다 검증 체크리스트

**각 Phase PR 머지 전 필수**:

- [ ] `tests/test_application/test_orchestrator.py` 그린 — 단일 4 함수 시그니처 변경 0
- [ ] `python scripts/run_pipeline.py --keyword "테스트키워드"` smoke pass
- [ ] `python scripts/analyze.py --keyword "..."` smoke pass
- [ ] `python scripts/generate.py --keyword "..."` smoke pass
- [ ] 기존 `POST /api/jobs` 응답 시간 회귀 없음
- [ ] `PatternCard.schema_version="2.0"` 호환성 (Phase 2 필드 추가 시 nullable 확인)
- [ ] BrightData 단일 호출이 배치 동시 실행 중에도 정상 (Phase 1 통합 테스트)
- [ ] `architecture-check.sh` 그린 — `domain/batch` 격리 검증

---

## 9. 위험 요소 (Risk Register)

| ID | 내용 | 완화 |
|---|---|---|
| B1 | 100개 full pipeline 실수 트리거로 비용·시간 폭주 | UI default = `analyze`, `pipeline` 명시 선택. `--max-cost-usd` flag 로 안전 cap |
| B2 | BrightData rate 폭주 → 단일 호출 503 | semaphore + 단일 web process 전제. 멀티 워커는 Redis advisory lock 도입 후 활성화 |
| B3 | Anthropic Batch API 24h SLA 초과 | Phase 3 야간 모드만 영향. timeout 보호 + 즉시 모드 자동 폴백 |
| B4 | 클러스터 잘못된 묶음 → SEO 기회 상실 | MVP 는 수동 cluster_id+cluster_role. 자동화는 Phase 5+ 컨펌 단계 동반 |
| B5 | `BatchJobManager` in-memory + web process 결합 → restart 시 진행 상태 손실 | DB 상태로 복구 가능 (in-progress 는 자동 retry 후 queued 복귀). Phase 3 worker 분리로 영구 해결 |
| B6 | FK 못 채워서 link 끊김 | Phase 1 은 `(job_id, slug, keyword)` triple. Phase 2 가 `GenerateResult` 보강 |
| B7 | Supabase row 폭증 (100건 × 단계별 usage) | api_usage 페이지네이션 이미 적용. batch_item 인덱스 사전 추가 |
| B8 | CSV 파싱 오류 → 잘못된 키워드 일괄 enqueue | csv_parser 가 검증 후 `created/skipped/failed` 분류. 사용자에게 사전 확인 step |

---

## 10. 핵심 설계 원칙 (10가지)

1. **단일 흐름 보존 절대** — `application/orchestrator.py` 4 함수 시그니처 불변
2. **Additive only** — 기존 파일 변경 0, 신규 파일만 추가 (Phase 2 의 `GenerateResult` 보강은 nullable 필드 추가만)
3. **수동 우선, 자동화는 Phase 5+** — 클러스터·발행 자동화는 검증된 후
4. **UI default 안전성** — `analyze` 기본, `pipeline` 명시 선택
5. **자원 격리** — JobManager 분리, BrightData semaphore (단일 프로세스 한정 명시)
6. **상태 머신 점진 확장** — Phase 1 은 단순, Phase 2 부터 세부 상태 활성
7. **Dual-mode 점진 활성** — Phase 1 은 `now` 만, `overnight`/`auto` 는 Phase 3
8. **PatternCard 모델 보호** — 재사용은 batch_item 컬럼만, 도메인 모델 손대지 않음
9. **FK nullable** — id 회수 보강 전엔 triple link, 회수 후 점진 정합화
10. **회귀 테스트가 단일 흐름 방패** — Phase 마다 단일 smoke + orchestrator 테스트 필수

---

## 11. Phase 5+ 확장 지점 (MVP 이후)

- **자동 클러스터링** — 임베딩 기반 + 사용자 컨펌 step. 정확도 검증 후 도입
- **GenerateResult 의 DB id 회수 표준화** — Phase 2 보강 결과를 SPEC-SEO-TEXT.md 에 정식 반영
- **멀티 worker / 멀티 인스턴스 운영** — Redis advisory lock + worker container 분리
- **검색 의도 분류 자동화** — keyword → intent (info/transactional/navigational) LLM 분류
- **카니발 자동 감지** — Phase 3 cluster_dedupe 가 발견 못한 의미 중복을 SOV 분석으로 탐지
- **자동 키워드 큐레이션** — 키워드 난이도 + 검색량 + 경쟁 SOV 종합 점수로 우선순위 자동 부여

---

## 변경 이력

- `2026-05-04`: v1 초안. Phase 1~4 정의, dual-mode (now/overnight/auto), 8 컬럼 CSV 스키마, `domain/batch` 격리 도메인. 외부 검토 4 라운드 반영 — operation 분기, mode now-only MVP, FK nullable triple link, PatternCard 모델 보호, cluster_role 명시.
- `2026-05-04`: Phase 2 PR1 부분 완료 — **FK 회수 + PatternCard 보관함**. `pattern_card.py._save_to_supabase` / `stage_runner._save_generated_to_supabase` 가 insert id 회수, 단일 흐름 결과 모델(AnalyzeResult/GenerateResult/PipelineResult)에 두 nullable id 필드 전파. `batch_orchestrator._run_operation` 이 `update_item_result` 로 keyword_batch_items FK 채움. 신규 `pattern_cards` 라우터 + `/patterns/by-id/[id]` 페이지. 단일 흐름 시그니처 무변경. 사전 필터·cluster·검수 큐는 PR2 (별도 차수).
- `2026-05-04`: Phase 2 PR2 부분 완료 — **사전 필터 + 클러스터 재사용**. `batch_orchestrator._dispatch_item` 이 `running` 마킹 직후 (1) 임계값 설정 시 `analyze_keyword` 호출 + min_search_volume/max_difficulty 검사 후 미달 키워드 자동 skipped, (2) `cluster_dedupe=True AND cluster_role=member` 면 같은 cluster 의 primary PatternCard 를 재사용해 분석 단계 압축. `cluster_dedupe` default = **False** (본문 유사도로 인한 1페이지 노출 리스크 보수 처리). 검수 큐·triple link 사후 백필은 PR3·PR4 로 분리.
- `2026-05-04`: Phase 2 PR3 부분 완료 — **검수 큐 + ready_to_publish 상태**. `_dispatch_item` 의 succeeded 마킹을 operation 별 분기로 정정: analyze→succeeded, generate/pipeline+compliance_passed=True→ready_to_publish, False/None→needs_review (데이터 누락 안전망). `ItemStatus` 에 `ready_to_publish` 추가 + `KeywordBatch.ready_to_publish_count` (in-memory 집계). `update_item_review` storage 함수 + `GET /batches/{id}/review` + `POST /batches/{id}/items/{item_id}/review` API + `/batches/[id]/review` 페이지 + `BatchReviewQueue` 컴포넌트. **운영 철학 정정**: 후보 키워드 모두 발행 대상, needs_review 는 폐기 X 발행 전 대기, 핵심 액션 approve/needs_fix (reject 는 dropdown 보조).
