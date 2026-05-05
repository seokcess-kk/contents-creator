# 키워드 배치 운영 시스템 (Batch Pipeline) — Spec v2

본 문서는 contents-creator 의 **대량 키워드 운영** 명세다.
SEO 트랙(SPEC-SEO-TEXT.md)·브랜드 카드 트랙(SPEC-BRAND-CARD.md)·순위 추적(SPEC-RANKING.md)과 **병행되는 운영 트랙**이며, 의존 방향은 단방향(batch → 단일 orchestrator 호출만).

작성: 2026-05-04
v2 정합화: 2026-05-05 — 운영 철학 정정 + Phase 2 (PR1~PR4) 완료 + UI/UX (PR-A~C) + B11~B14 반영
연관: tasks/todo.md "Batch Pipeline MVP" 섹션, application/CLAUDE.md, SPEC-SEO-TEXT.md §12

---

## 0. 운영 철학 (불변, 모든 설계의 토대)

이 시스템의 초기 목표는 **후보 키워드를 줄이는 것이 아니라**, 사용자가 입력한 키워드를 **모두 발행 대상**으로 보고 발행 전후 데이터를 빠짐없이 쌓아 사후 분석에 활용하는 것이다.

분석 데이터(검색량/난이도/SERP 구성)는 **발행 여부 판단이 아니라** "왜 어떤 키워드는 상위 노출되고 어떤 키워드는 실패했는지" 학습할 사후 스냅샷이다.

### 행동 규칙

- **사전 필터(min_search_volume / max_difficulty) default OFF** — 운영자가 명시 설정 시만
- **`cluster_dedupe` default OFF** — 본문 유사도 1페이지 노출 리스크 보수 처리
- **`needs_review` 는 폐기/발행 중단이 아닌 "발행 전 확인/수정 대기"**
- **검수 핵심 액션 = `approve` / `needs_fix`** — `reject` 는 예외 상태 (UI dropdown 보조)
- **`succeeded` 의미 분리** — analyze 만 끝난 item 만 succeeded. generate/pipeline 완료물은 `ready_to_publish`
- **`approved` 는 `status` 가 아닌 `review_status` 한정 메타** — needs_review → ready_to_publish 직접 전환

### 상태 머신

```
candidate → generated
generated + compliance OK             → ready_to_publish
generated + compliance fail/unknown   → needs_review
needs_review + review_status=approved → ready_to_publish
ready_to_publish → published → tracking
```

예외: `failed_generation` / `url_missing` / `needs_fix` / `rejected`

---

## 1. 목적

100개 이상의 키워드를 단건 CLI/웹 호출로 처리하던 한계를 넘어, **CSV 한 번 업로드로 분석·생성·검수·발행 준비까지 자동화**하고, 발행 후 순위 궤적을 종단 추적해 운영 학습에 사용한다.

- 사용자 조작 공수 95% 절감 (100건 클릭 → 1회 업로드)
- **모든 후보 키워드 발행 대상** — 분석은 사후 학습 스냅샷
- 검수 부담 자동화 — 의료법 위반·미달은 needs_review 자동 마킹, 운영자 일괄 승인
- 발행 후 D+1/3/7/14/30 순위 궤적 자동 누적 → 인사이트 도출
- 야간 LLM 비용 절감 (Anthropic Batch API adapter, Phase 3)

**명시 비목표**:

- **단일 흐름 변경 0** — 기존 `scripts/run_pipeline.py`, `POST /api/jobs`, `application/orchestrator.py` 4 함수는 그대로 동작
- **자동 클러스터링 X** — 사용자 입력 `cluster_id` 만. 자동화는 데이터 누적 후 Phase 5+
- **자동 발행 강제 X** — 검수 통과 후 사용자가 네이버 직접 발행 → URL 등록 → publications 진입 (Phase 4 의 자동 등록도 opt-in)

---

## 2. 핵심 원칙 (불변)

1. **단일 흐름 100% 보존** — `application/orchestrator.py` 4 함수 시그니처 불변, 기존 CLI/웹 API 무수정 (additive only)
2. **Dual-mode** — `now`(일반 API) / `overnight`(Anthropic Batch API) / `auto`(priority 기반 라우팅). **Phase 1~2 는 `now` 만 처리**, `overnight`·`auto` 는 DB/API 받되 `400 Not Supported Yet`
3. **자원 격리** — `JobManager`(단일 전용) ↔ `BatchJobManager`(배치 전용) 분리. BrightData 동시성은 단일 프로세스 semaphore (Phase 1~2 안전망 한정 — 멀티 워커 진입 시 Redis advisory lock 필요)
4. **수동 우선** — 클러스터링은 사용자 입력 `cluster_id` + `cluster_role` 부터. 자동 클러스터링은 운영 데이터 누적 후
5. **UI default = `analyze`** — 100개 full pipeline 실수 차단. `pipeline` 은 명시 선택만 가능
6. **PatternCard 모델 무수정** — 재사용은 `keyword_batch_items.pattern_card_id` 로만 표현. `PatternCard.schema_version` 은 그대로 `2.0`
7. **FK 회수 graceful** — Supabase 미설정/실패 시 None 으로 propagate (운영 데이터 누락 방지). PR4 의 triple link backfill 도구로 사후 보강
8. **검수 큐 의미 분리** (운영 철학 §0): `succeeded` ≠ `ready_to_publish`. 발행 가능한 본문은 `ready_to_publish`. analyze 만 끝난 item 만 `succeeded` 유지

---

## 3. 단계별 파이프라인

### Phase 1 (3~4일) — 배치 인프라 + operation 분기 + retry + dashboard ✅ 완료

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
※ `analyzing → ready_to_generate → generating` 등 세부 상태는 enum 에 정의됐지만 실사용 안 함 (dead state 방치).

---

### Phase 2 (전체 PR1~PR4 완료) — FK 회수 + 사전 필터 + cluster 재사용 + 검수 큐 + Triple link 백필 ✅

**가치**: 100→30~50 압축 + 검수 효율 5~10배 + 발행 → 순위 추적 종단 연결

#### 사전 필터 (PR2)
- `min_search_volume` (batch 단위, default None) — 검색량 미달 → `skipped` (운영 철학상 default OFF)
- `max_difficulty` (batch 단위, default None) — 난이도 초과 → `skipped`
- `cluster_dedupe` (default **False** — PR2 보수 결정) — 명시적 ON 시만 같은 cluster 재사용 활성

#### Cluster 재사용 (PR2)
1. `cluster_role=primary` 만 분석 → PatternCard 생성 → `keyword_batch_items.pattern_card_id` 저장
2. 같은 cluster 의 `member` 들은 primary 의 `pattern_card_id` 그대로 참조 (analyze 는 즉시 succeeded, generate/pipeline 은 [6]~[10] 만 실행)
3. primary 재사용 가능 status: `succeeded`, `ready_to_publish`, `needs_review` (PatternCard 가 만들어진 모든 종결 상태)
4. primary polling — `batch_cluster_primary_timeout_sec` (default 600초) 까지 대기, 실패/타임아웃 시 자체 분석 폴백
5. `PatternCard` 모델은 무수정 (재사용 관계는 batch_item 쪽 컬럼만)

**클러스터 재사용 사용 가이드**:
- **권장 묶음**: 같은 의도의 long-tail 변형 — `다이어트 한의원 추천` ↔ `좋은 다이어트 한의원`
- **분리 묶음**: 지역·브랜드·intent 가 다른 키워드 — `강남 다이어트 한의원` 과 `역삼 다이어트 한의원` 은 같은 cluster 로 묶지 말 것 (본문 유사도로 1페이지 노출 어려워질 수 있음)
- **default OFF** — 운영자가 키워드 묶음을 검토 후 명시적으로 `--cluster-dedupe` (CLI) / checkbox ON (Web) / `cluster_dedupe=true` (API) 로 켤 때만 활성

#### 상태 머신 (Phase 2 — 운영 철학 §0 반영, 실 구현)
```
analyze 만 끝난 item                                 → succeeded
generate/pipeline + compliance_passed=True           → ready_to_publish
generate/pipeline + compliance_passed=False          → needs_review
generate/pipeline + compliance_passed=None (안전망)   → needs_review
needs_review + review action approve                 → review_status=approved + status=ready_to_publish
needs_review + review action needs_fix               → review_status=needs_fix (status 그대로)
needs_review + review action reject                  → review_status=rejected (예외, status 그대로)
                                                     ↘ skipped (사전 필터)
```

#### FK 정합성 보강 (PR1)
- `application/models.py` 의 `AnalyzeResult` / `GenerateResult` / `PipelineResult` 에 `pattern_card_id` / `generated_content_id` nullable 필드 추가 (시그니처 매개변수 무변경, 반환 모델 확장만)
- `application/stage_runner._save_generated_to_supabase` 가 `(generated_content_id, pattern_card_id)` tuple 반환
- `domain/analysis/pattern_card.save_pattern_card` 가 `(Path, supabase_id)` tuple 반환
- `batch_orchestrator._run_operation` 이 회수한 id 를 `storage.update_item_result` 로 저장
- Supabase 미설정/실패 시 graceful (None 채움 + warning)
- PR4 의 `(job_id, slug, keyword)` triple link backfill 로 사후 보강 가능

#### 검수 큐 (PR3 + UI/UX PR-A)
- `/batches/{id}/review` 페이지 + `BatchReviewQueue` 컴포넌트
- review_status 4 탭: 검수 대기 / 수정 필요 / 승인됨 / 거부됨
- 일괄 승인 (체크박스 + 선택 일괄 approve)
- 액션 후 5초 toast + Undo (revert action 으로 review_status=pending + status=needs_review 복원)
- 검수자 이름 localStorage 자동 저장
- 의료법 위반 카테고리 hover tooltip (Phase B14, `compliance_violations` jsonb)
- `BatchProgressTable` 헤더에 "→ 검수 큐 (N)" / "→ 발행 준비 (N)" link
- skipped 사유 amber 강조 (정상 흐름 신호)
- `/batches` 목록의 "검수 필요 (N)" 컬럼 클릭 → review 페이지 직링크

#### 발행 준비 큐 (UI/UX PR-C)
- `/batches/{id}/publish` 페이지 — `status=ready_to_publish` 만 표시
- "URL 등록" prominent 버튼 → `/results/{slug}` PublicationForm
- target_url 미리보기 + publication_id 등록 완료 표시

#### Triple link 사후 백필 (PR4)
- `find_pattern_card_by_triple(slug, keyword)` + `find_generated_content_by_triple(job_id, slug, keyword)` storage
- `backfill_unlinked_items(batch_id)` use case (idempotent)
- `POST /batches/{id}/backfill-fk` API + `scripts/run_batch.py --backfill-fk` CLI
- fire-and-forget 회수 실패 케이스 사후 보강. 자동 cron 미사용 — 운영자 명시 호출

---

### Phase 3 (3~4일) — Anthropic Batch API adapter (LLM 독립 호출 한정) + worker process 분리 ⏸ 외부 의존 미충족

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
if item.mode == "now" or (item.mode == "auto" and item.priority <= 3):
    enqueue_immediate(item)              # 일반 API 큐
elif item.mode == "overnight" or (item.mode == "auto" and item.priority >= 4):
    enqueue_overnight_with_batch_api(item)  # 야간 worker + LLM 독립 호출만 batch API
```

**Worker process 분리**:
- Phase 1~2 의 `BatchJobManager` 는 web process in-memory MVP
- Phase 3 부터 별도 worker process 또는 Render cron command 로 분리
- 야간 시작 시간 (default 22:00 KST) 에 `mode="overnight" + status="queued"` 일괄 처리

**멀티 워커 진입 시 자원 보호**:
- BrightData 단일 프로세스 semaphore 한계 도달 → Redis 또는 Supabase advisory lock 으로 전역 한도 강제

**외부 prerequisite**:
- 🔑 Anthropic Batch API endpoint 사용량 분리 추적
- 🏗️ Redis 인스턴스 (advisory lock)
- 🚀 Render worker service 또는 cron 분리

---

### Phase 4 (2~3일) — 알림 + publication 자동 등록 ⏸ 외부 의존 미충족

**알림 채널** (env 미설정 시 스킵):
- `SLACK_WEBHOOK_URL` (권장)
- 또는 이메일 (Resend, SendGrid)

**알림 트리거**:
- 배치 완료 — 요약 (ready_to_publish N / needs_review M / failed K / cost $X)
- 검수 큐 누적 임계 — needs_review 가 일정 수 이상이면 알림
- 의료법 위반 발견 (개별) — 키워드 + 위반 카테고리
- 배치 전체 실패 — 즉시 알림
- 야간 batch 시작/종료

**publication 자동 등록 — 운영 철학 §0 반영 정정** (opt-in):
- 운영 철학상 후보 키워드 모두 발행 대상이지만, **실제 발행은 운영자가 네이버 블로그 직접 수행** (자동 발행 X). publications 등록도 명시적 opt-in.
- `target_url` 컬럼 채워진 item 중 status=`ready_to_publish` AND `auto_publish_enabled=true` (batch 단위) → `publications` 자동 INSERT
- → `/rankings` 추적 사이클 자동 진입
- env 미설정 또는 `auto_publish_enabled=false` 시 비활성화 (사용자가 검수 큐에서 수동 URL 등록만 가능)
- `quality_score` 임계값은 보조 게이트, 핵심 결정은 review_status=approved

**외부 prerequisite**:
- 🔗 Slack incoming webhook URL
- 📋 auto publish 정책 명시 결정 (compliance 통과만 / 모든 ready_to_publish / 운영자 명시 opt-in)

---

## 4. Supabase 스키마

```sql
-- 배치 메타
create table keyword_batches (
  id uuid primary key default uuid_generate_v4(),
  name text,
  mode text not null default 'now',          -- 'now' | 'overnight' | 'auto' (Phase 1~2 는 now 만)
  status text not null default 'queued',     -- queued/running/completed/failed/cancelled
  total_count int not null,
  succeeded_count int default 0,             -- analyze 만 끝난 item (Phase 2 의미 분리)
  failed_count int default 0,
  skipped_count int default 0,
  needs_review_count int default 0,
  estimated_cost_usd numeric default 0,
  -- 사전 필터 임계값 (Phase 2)
  min_search_volume int,
  max_difficulty text,
  cluster_dedupe boolean default false,      -- ⚠️ 운영 철학상 default false (PR2 보수)
  -- Phase 4 자동 발행 (opt-in)
  auto_publish_enabled boolean default false,
  created_at timestamptz default now(),
  started_at timestamptz,
  completed_at timestamptz
);
-- ※ ready_to_publish_count 는 DB 컬럼 미정의 — count_items_by_status 가 in-memory 재집계.

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
  -- queued / running / succeeded / ready_to_publish / needs_review / failed / skipped
  -- (운영 철학 §0 — succeeded 는 analyze 만, ready_to_publish 가 발행 가능 본문)
  retry_count int not null default 0,
  max_retries int not null default 2,
  job_id text,                               -- 단일 job 추적 (PR1 link 키)
  error text,
  estimated_cost_usd numeric default 0,

  -- 분석 결과 (PR2 사전 필터 메타)
  search_volume int,
  difficulty_grade text,                     -- LOW / MEDIUM / HIGH / MISSING

  -- 생성 결과 (PR1 회수)
  pattern_card_id uuid references pattern_cards(id),
  generated_content_id uuid references generated_contents(id),
  quality_score numeric,
  compliance_passed boolean,
  compliance_violations jsonb default '[]'::jsonb,  -- ⭐ B14 추가: 위반 카테고리 리스트

  -- 검수 (PR3)
  review_status text default 'pending',      -- pending / approved / rejected / needs_fix
  reviewer text,
  reviewed_at timestamptz,

  -- 발행 (PR3 fix round 2 + Phase 4)
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

**ALTER 마이그레이션** (idempotent — 기존 환경 호환):
```sql
-- B14
alter table keyword_batch_items
    add column if not exists compliance_violations jsonb default '[]'::jsonb;
-- generated_contents.keyword (UI/UX hotfix 권고)
alter table generated_contents add column if not exists keyword text;
```

**롤백 SQL**:
```sql
drop table if exists keyword_batch_items;
drop table if exists keyword_batches;
```

**FK nullable 원칙**: `pattern_card_id`, `generated_content_id`, `publication_id`, `brand_id` 모두 nullable. PR1 회수 graceful + PR4 사후 백필.

---

## 5. 데이터 모델 (Pydantic)

```python
# domain/batch/model.py
ItemStatus = Literal[
    "queued", "running",
    "succeeded",        # analyze 만 끝남 (운영 철학 §0)
    "ready_to_publish", # ⭐ B9 추가: 발행 준비 (compliance OK)
    "needs_review",     # 발행 전 확인/수정 대기 (폐기 X)
    "failed", "skipped",
    # dead — Phase 2 미사용
    "analyzing", "ready_to_generate", "generating",
]
ReviewStatus = Literal["pending", "approved", "rejected", "needs_fix"]


class KeywordBatch(BaseModel):
    id: str | None = None
    name: str | None = None
    mode: Literal["now", "overnight", "auto"] = "now"
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    total_count: int
    succeeded_count: int = 0           # analyze 만
    failed_count: int = 0
    skipped_count: int = 0
    needs_review_count: int = 0
    ready_to_publish_count: int = 0    # ⭐ Pydantic only (DB 컬럼 X, in-memory 집계)
    estimated_cost_usd: float = 0
    min_search_volume: int | None = None
    max_difficulty: str | None = None
    cluster_dedupe: bool = False       # ⚠️ default False (운영 철학)
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

    status: ItemStatus = "queued"
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
    compliance_violations: list[str] = Field(default_factory=list)  # ⭐ B14

    review_status: ReviewStatus = "pending"
    reviewer: str | None = None
    reviewed_at: datetime | None = None

    publication_id: str | None = None
    published_at: datetime | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class BatchEnqueueResult(BaseModel):
    batch_id: str
    total: int
    created: int
    skipped: list[dict[str, str]] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)
```

---

## 6. 디렉터리 구조 (실 구현 반영)

```
domain/
└── batch/                            # 격리 도메인 (STAGE_ORDER[batch]=0)
    ├── __init__.py
    ├── model.py                      # KeywordBatch, KeywordBatchItem 등 Pydantic
    ├── csv_parser.py                 # CSV → KeywordBatchItem 리스트 변환 + 검증
    ├── storage.py                    # Supabase CRUD
    └── CLAUDE.md                     # 도메인 규칙

application/
├── batch_orchestrator.py             # enqueue/dispatch/retry/cancel + cluster 재사용 + 사전 필터 + 백필
├── batch_job_manager.py              # worker pool (단일 JobManager 와 분리)
├── performance_orchestrator.py       # ⭐ B12: D+N 순위 궤적
└── insights_orchestrator.py          # ⭐ B13: 난이도/검색량 × Top10 진입 통계

web/api/routers/
├── batches.py                        # 배치 CRUD + 검수 큐 + 발행 준비 큐 + 백필
├── pattern_cards.py                  # ⭐ PR1: PatternCard 보관함 라우터
├── pipeline.py                       # ⭐ B11: 통합 파이프라인 대시보드
├── performance.py                    # ⭐ B12
└── insights.py                       # ⭐ B13

scripts/
└── run_batch.py                      # CLI (--backfill-fk 포함)

web/frontend/src/
├── app/
│   ├── batches/
│   │   ├── page.tsx                  # 배치 목록 + 진행 dashboard
│   │   ├── [id]/page.tsx             # 단건 + item list
│   │   ├── [id]/review/page.tsx      # ⭐ PR3: 검수 큐
│   │   └── [id]/publish/page.tsx     # ⭐ PR-C: 발행 준비 큐
│   ├── pipeline/page.tsx             # ⭐ B11: 통합 파이프라인
│   ├── performance/page.tsx          # ⭐ B12
│   ├── insights/page.tsx             # ⭐ B13
│   └── patterns/by-id/[id]/page.tsx  # ⭐ PR1: PatternCard 상세
└── components/
    ├── BatchUploadForm.tsx           # CSV/textarea + 사전 필터 옵션
    ├── BatchProgressTable.tsx        # poll 기반 진행률 + 진행 bar + 결과 link
    └── BatchReviewQueue.tsx          # 검수 큐 4 탭 + 일괄 승인 + Undo + violation tooltip

tests/
├── test_batch/                       # 도메인 (csv_parser, storage)
├── test_application/test_batch_orchestrator.py
├── test_application/test_batch_prefilter.py
├── test_application/test_batch_cluster.py
├── test_application/test_batch_job_manager.py
├── test_application/test_pr1_id_propagation.py
├── test_web/test_batches_api.py
└── test_web/test_pattern_cards_router.py

config/
└── schema.sql                        # 2 테이블 + ALTER 누적
```

**`domain/batch` 격리 규칙**:
- `domain/batch` → 다른 도메인 import 금지 (격리)
- `application/batch_orchestrator` 가 `domain/batch` + `application.orchestrator` 합성
- `architecture-check.sh` 의 `STAGE_ORDER[batch]=0` 등록

---

## 7. 실행 방법

```bash
# CSV 업로드 (Phase 1~2, mode=now 만)
python scripts/run_batch.py \
  --csv keywords.csv \
  --mode now \
  --name "2026-Q2 천안 다이어트 캠페인"

# Phase 2 옵션 — 사전 필터 + 클러스터 재사용 (모두 default OFF)
python scripts/run_batch.py --csv keywords.csv --mode now \
  --min-search-volume 200 --max-difficulty MEDIUM \
  --cluster-dedupe                                    # 명시 ON

# 진행 상태 조회
python scripts/run_batch.py --status <batch_id>

# 단건 재시도 (실패 / ready_to_publish / needs_review item)
python scripts/run_batch.py --retry-item <item_id>

# 배치 취소 (queued items 만)
python scripts/run_batch.py --cancel <batch_id>

# Triple link 사후 백필 (PR4) — fire-and-forget 회수 실패 보강
python scripts/run_batch.py --backfill-fk <batch_id>

# Phase 3~4 (점진 활성)
python scripts/run_batch.py --csv keywords.csv --mode overnight  # Phase 3
python scripts/run_batch.py --csv keywords.csv --auto-publish    # Phase 4
```

**웹 UI** — `/batches` 페이지에서 동일 기능. CSV 업로드 + 옵션 폼 + dashboard.

**환경변수** (Phase 별 추가):

| Phase | env | 기본값 | 의미 |
|---|---|---|---|
| 1 | `BATCH_MAX_WORKERS` | 2 | 동시 worker 수 |
| 1 | `BRIGHTDATA_CONCURRENT_LIMIT` | 5 | semaphore 한도 |
| 2 | `BATCH_CLUSTER_PRIMARY_TIMEOUT_SEC` | 600 | cluster member primary 대기 타임아웃 |
| 2 | `BATCH_CLUSTER_POLL_INTERVAL_SEC` | 1.0 | cluster polling 주기 |
| 2 | `BATCH_MIN_SEARCH_VOLUME` | (none) | 사전 필터 default 임계값 (운영 철학상 default OFF) |
| 2 | `BATCH_MAX_DIFFICULTY` | (none) | 사전 필터 default 난이도 상한 |
| 3 | `OVERNIGHT_START_HOUR` | 22 | 야간 worker 시작 시각 (KST) |
| 3 | `BATCH_WORKER_PROCESS` | false | true 면 별도 process 분리 |
| 4 | `SLACK_WEBHOOK_URL` | (none) | 알림 webhook |
| 4 | `AUTO_PUBLISH_THRESHOLD` | 85 | quality_score 보조 게이트 (핵심은 review_status=approved) |

---

## 8. 단일 흐름 보호 — Phase 마다 검증 체크리스트

**각 Phase PR 머지 전 필수**:

- [ ] `tests/test_application/test_orchestrator.py` 그린 — 단일 4 함수 시그니처 변경 0
- [ ] `tests/test_application/test_pr1_id_propagation.py` — 단일 흐름 ↔ batch storage cross-coupling 0 검증
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
| B4 | 클러스터 잘못된 묶음 → 본문 유사도로 두 키워드 모두 1페이지 노출 페널티 | **default OFF** (PR2 보수). SPEC §3 Phase 2 의 사용 가이드 + PR3 차별화 검증 (Jaccard) 후속 |
| B5 | `BatchJobManager` in-memory + web process 결합 → restart 시 진행 상태 손실 | DB 상태로 복구 가능 (in-progress 는 자동 retry 후 queued 복귀). Phase 3 worker 분리로 영구 해결 |
| B6 | FK 못 채워서 link 끊김 | PR1 graceful (None 으로 propagate) + PR4 backfill 도구로 사후 보강 |
| B7 | Supabase row 폭증 (100건 × 단계별 usage) | api_usage 페이지네이션 이미 적용. batch_item 인덱스 사전 추가 |
| B8 | CSV 파싱 오류 → 잘못된 키워드 일괄 enqueue | csv_parser 가 검증 후 `created/skipped/failed` 분류. 사용자에게 사전 확인 step |
| B9 | 운영자가 succeeded 카운트만 보고 발행 가능한 줄 오해 | UI 라벨 "분석 완료" / "발행 준비" 분리. nav 의 "키워드 파이프라인" 통합 대시보드로 일관 시각화 |
| B10 | review API 가 다른 batch 의 item 변경 가능 | review_item / retry_item 모두 `item.batch_id == batch_id` 검증 (review feedback round 2 fix) |
| B11 | 검수 중 실수 (잘못된 일괄 승인) | toast Undo 5초 + revert action (review_status=pending + status=needs_review 복원) |
| B12 | DB 컬럼 마이그레이션 미적용으로 select 깨짐 | storage 가 try/except graceful retry (B14 의 compliance_violations + UI/UX hotfix 의 keyword 컬럼) |

---

## 10. 핵심 설계 원칙 (10가지)

1. **단일 흐름 보존 절대** — `application/orchestrator.py` 4 함수 시그니처 불변
2. **Additive only** — 기존 파일 변경 0, 신규 파일만 추가 (PR1 의 `GenerateResult` 보강은 nullable 필드 추가만)
3. **수동 우선, 자동화는 Phase 5+** — 클러스터·발행 자동화는 검증된 후
4. **UI default 안전성** — `analyze` 기본, `pipeline` 명시 선택. `cluster_dedupe` default OFF
5. **자원 격리** — JobManager 분리, BrightData semaphore (단일 프로세스 한정 명시)
6. **상태 머신 운영 철학 우선** — succeeded ≠ ready_to_publish, needs_review = 발행 전 대기
7. **Dual-mode 점진 활성** — Phase 1~2 는 `now` 만, `overnight`/`auto` 는 Phase 3
8. **PatternCard 모델 보호** — 재사용은 batch_item 컬럼만, 도메인 모델 손대지 않음
9. **FK graceful + 사후 backfill** — id 회수 실패는 정상 케이스. PR4 도구로 보강
10. **회귀 테스트가 단일 흐름 방패** — Phase 마다 단일 smoke + orchestrator 테스트 필수

---

## 11. 운영 화면 (사용자 §9 — 구현 현황)

| 화면 | 경로 | 상태 | 설명 |
|---|---|---|---|
| 키워드 파이프라인 | `/pipeline` | ✅ B11 | 모든 batch 합산. candidate→ready_to_publish→published 단계별 카운트 + 단계별 keyword 목록 |
| 발행 성과 | `/performance` | ✅ B12 | 발행된 publication 의 D+1/3/7/14/30 순위 궤적 + best/current + Top10 일수 |
| 인사이트 | `/insights` | ✅ B13 | 난이도/검색량 × Top10 진입율, D+N 진입 비율. compliance × 평균 best 는 후속 |
| 배치 운영 | `/batches` | ✅ Phase 1~2 | 배치 목록 + 컬럼 (분석 완료/발행 준비/검수 필요) + 검수 직링크 |
| 검수 큐 | `/batches/[id]/review` | ✅ PR3+PR-A | 4 탭 + 일괄 승인 + Undo + violation tooltip |
| 발행 준비 큐 | `/batches/[id]/publish` | ✅ PR-C | ready_to_publish 만 — URL 등록 prominent action |
| PatternCard 보관함 | `/patterns/by-id/[id]` | ✅ PR1 | 분석 결과 상세 (distributions, sections, DIA+) |

**후속 (Phase 5+)**:
- Publishing Queue 통합 (모든 batch 합쳐 ready_to_publish 모음)
- Performance 페이지의 publication detail (일별 시계열 chart)
- Insights 의 cluster 그룹별 / 블로그별 / 콘텐츠 구조별 성과 분리

---

## 12. Phase 5+ 확장 지점 (MVP 이후)

- **자동 클러스터링** — 임베딩 기반 + 사용자 컨펌 step. 정확도 검증 후 도입
- **GenerateResult 의 DB id 회수 표준화** — Phase 2 보강 결과를 SPEC-SEO-TEXT.md 에 정식 반영
- **멀티 worker / 멀티 인스턴스 운영** — Redis advisory lock + worker container 분리
- **검색 의도 분류 자동화** — keyword → intent (info/transactional/navigational) LLM 분류
- **카니발 자동 감지** — Phase 3 cluster_dedupe 가 발견 못한 의미 중복을 SOV 분석으로 탐지
- **자동 키워드 큐레이션** — 키워드 난이도 + 검색량 + 경쟁 SOV 종합 점수로 우선순위 자동 부여
- **본문 차별화 검증 (PR3 후속)** — cluster reuse 시 outline negative example 주입 + Jaccard 유사도 측정 후 needs_review 마킹
- **검수 큐 detail view** — compliance 위반 카테고리 별 통계 + 위반 패턴 학습
- **Insights 확장** — cluster_id 그룹별 / 블로그별 / 콘텐츠 구조 (DIA+) 별 성과 패턴

---

## 변경 이력

- `2026-05-04`: v1 초안. Phase 1~4 정의, dual-mode (now/overnight/auto), 8 컬럼 CSV 스키마, `domain/batch` 격리 도메인. 외부 검토 4 라운드 반영 — operation 분기, mode now-only MVP, FK nullable triple link, PatternCard 모델 보호, cluster_role 명시.
- `2026-05-04`: Phase 2 PR1 — **FK 회수 + PatternCard 보관함**. `pattern_card.py._save_to_supabase` / `stage_runner._save_generated_to_supabase` 가 insert id 회수, 단일 흐름 결과 모델에 두 nullable id 필드 전파. `batch_orchestrator._run_operation` 이 `update_item_result` 로 keyword_batch_items FK 채움. 신규 `pattern_cards` 라우터 + `/patterns/by-id/[id]` 페이지. 단일 흐름 시그니처 무변경. (commit `2582d72`)
- `2026-05-04`: Phase 2 PR2 — **사전 필터 + 클러스터 재사용**. `batch_orchestrator._dispatch_item` 이 `running` 마킹 직후 (1) 임계값 설정 시 `analyze_keyword` 호출 + min_search_volume/max_difficulty 검사 후 미달 키워드 자동 skipped, (2) `cluster_dedupe=True AND cluster_role=member` 면 같은 cluster 의 primary PatternCard 를 재사용해 분석 단계 압축. `cluster_dedupe` default = **False** (본문 유사도로 인한 1페이지 노출 리스크 보수 처리). (commit `59a5f86`)
- `2026-05-04`: Phase 2 PR3 — **검수 큐 + ready_to_publish 상태**. `_dispatch_item` 의 succeeded 마킹을 operation 별 분기로 정정: analyze→succeeded, generate/pipeline+compliance_passed=True→ready_to_publish, False/None→needs_review (데이터 누락 안전망). `ItemStatus` 에 `ready_to_publish` 추가 + `KeywordBatch.ready_to_publish_count` (in-memory 집계). `update_item_review` storage + `GET /batches/{id}/review` + `POST /batches/{id}/items/{item_id}/review` API + `/batches/[id]/review` 페이지 + `BatchReviewQueue` 컴포넌트. **운영 철학 정정**: 후보 키워드 모두 발행 대상, needs_review 는 폐기 X 발행 전 대기, 핵심 액션 approve/needs_fix (reject 는 dropdown 보조). (commit `042c90c`)
- `2026-05-04`: Phase 2 PR4 — **Triple link 사후 백필 운영 도구**. `find_pattern_card_by_triple` + `find_generated_content_by_triple` (job_id None 시 1차 스킵) + `backfill_unlinked_items` (idempotent) + `POST /batches/{id}/backfill-fk` API + CLI. **Phase 2 전체 완료**. (commit `e95f6c3`)
- `2026-05-04`: review feedback fix round 1 — cluster primary 재사용 status 확장 (ready_to_publish + needs_review), review/retry API batch_id 소속 검증, terminal no-op 확장, ResultLinks status 의존 제거, backfill still_unlinked 부분 매칭. (commit `3bc7d90`)
- `2026-05-04`: review feedback fix round 2 — list_batches counters 재집계 + UI 라벨 정정 (분석 완료 / 발행 준비) + publication ↔ batch_item.publication_id 백필 (`_attach_batch_item`) + BatchProgressTable 상세 필터에 ready_to_publish/needs_review 추가. (commit `e635f00`)
- `2026-05-04`: UI/UX PR-A — 검수 큐 일괄 승인 + 5초 toast Undo (revert action) + 검수자 localStorage + ResultLinks status 별 강조 라벨 (발행 준비/검수/결과) + /batches 목록 검수 필요 컬럼 직링크 + 빈 상태 안내. (commit `fcf33b1`)
- `2026-05-04`: UI/UX PR-B — /results/{slug} keyword 정정 (slug 추정 → generated_contents.keyword fetch) + 검수 큐 review_status 4 탭 (대기/수정 필요/승인됨/거부됨) + skipped 사유 amber 강조 + BatchProgressTable 진행률 progress bar + 모바일 반응형. (commit `72afb37`)
- `2026-05-04`: UI/UX PR-C — `/batches/[id]/publish` 발행 준비 큐 페이지 신규 + URL 등록 prominent + BatchItem 타입 보강 (intent/region/brand_id/target_url/memo). (commit `af7afb1`)
- `2026-05-04`: hotfix `/api/results/recent` — generated_contents.keyword 컬럼 미적용 환경 graceful fallback (keyword 빼고 retry). (commit `57547ea`)
- `2026-05-05`: Phase B11 — **Keyword Pipeline 통합 대시보드** (`/pipeline`). `aggregate_pipeline_counts` 모든 batch 합산 + `list_items_by_global_status`. 7 status 카드 + published/total + 단계별 keyword 목록 + quick action. nav 첫 진입점. (commit `15e4125`)
- `2026-05-05`: Phase B12 — **발행 성과 대시보드** (`/performance`). `performance_orchestrator.get_publication_trajectory` D+1/3/7/14/30 매칭 + best/current + Top10 일수. 요약 4 카드 + publication 표 (순위별 색상). (commit `1b84ec3`)
- `2026-05-05`: Phase B13 — **인사이트** (`/insights`). 난이도/검색량 × Top10 진입율 + D+N 진입 비율. sample_size 0 시 graceful 안내. (commit `c53bae1`)
- `2026-05-05`: Phase B14 — **검수 큐 위반 카테고리 tooltip**. ComplianceReport.violations → `compliance_violations: list[str]` propagation (PipelineResult/GenerateResult/KeywordBatchItem). storage update_item_result graceful (jsonb 컬럼 미적용 시 빼고 retry). schema.sql ALTER 추가. BatchReviewQueue 의 ComplianceCell 한글 카테고리 (효과 과장 / 1인칭 홍보 / ...) hover. (commit `6993d64`)
- `2026-05-05`: SPEC-BATCH **v2 정합화** — 운영 철학 §0 신설, Phase 2 상태 머신·검수 큐·UI/UX 반영, §4 schema 의 cluster_dedupe default false + compliance_violations + ready_to_publish 명시, §5 Pydantic 모델 갱신, §7 환경변수 + Phase 2 누락 항목 추가, §9 risk register 4 항목 추가 (B9~B12), §11 운영 화면 표 신설.
