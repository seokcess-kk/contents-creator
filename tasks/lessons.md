# Lessons — 실수 패턴 & 교훈

> 사용자 교정이나 반복 실수 발견 시 이 파일에 기록.
> 세션 시작 시 이 파일을 리뷰. 반복 패턴 발견 시 `CLAUDE.md` 에 규칙으로 승격.

## 카테고리 인덱스

> 본문은 시간순. 빠른 탐색용 카테고리 매핑 (2026-05-08 추가).

### Compliance / 의료법
- [SEO 원고 파이프라인 교훈](#seo-원고-파이프라인-교훈-2026-04-16) — 2026-04-16

### Build / Test / CI
- [vitest fake timer + waitFor 비호환 + Response 1회 read 함정](#vitest-fake-timer--waitfor-비호환--response-1회-read-함정-2026-05-08) — 2026-05-08
- [build-check.sh 의 pytest 는 system python — venv 와 의존 동기화 필수](#build-checksh-의-pytest-는-system-python-사용--venv-와-의존-동기화-필수-2026-05-08) — 2026-05-08
- [Windows cp949 콘솔 + Python 한글 처리 — Polish P4](#windows-cp949-콘솔--python-한글-처리--polish-p4-2026-05-06) — 2026-05-06
- [테스트에서 SWR 캐시 격리 — `SWRConfig provider: () => new Map()`](#테스트에서-swr-캐시-격리--swrconfig-provider---new-map-2026-05-07) — 2026-05-07

### Deploy / Infrastructure
- [Chrome 136+ App-Bound Encryption v20 — CDP 자동 로그인 봉쇄](#chrome-136-app-bound-encryption-v20--cdp-자동-로그인-봉쇄-2026-05-10) — 2026-05-10
- [Outline 실패 다층 진단 — silent except + max_tokens × OOM + 영속화 비활성](#outline-실패-다층-진단--silent-except--max_tokens--oom--영속화-비활성-2026-05-10) — 2026-05-10
- [In-memory JobManager 휘발 + 폴링 retry-bound 패턴](#in-memory-jobmanager-휘발--폴링-retry-bound-패턴-2026-05-08) — 2026-05-08
- [Vercel 함수 페이로드 4.5MB 한계 — Presigned URL 우회](#vercel-함수-페이로드-45mb-한계--presigned-url-우회-2026-04-30) — 2026-04-30
- [In-process APScheduler + 단일 컨테이너 = cron 누락 함정](#in-process-apscheduler--단일-컨테이너--cron-누락-함정-2026-05-03) — 2026-05-03
- [save_usage_to_supabase silent failure + 자동 검증](#save_usage_to_supabase-silent-failure--자동-검증-2026-05-03) — 2026-05-03
- [Mutating endpoint 에 외부 retry 거는 패턴 = lock 충돌 폭발](#mutating-endpoint-에-외부-retry-거는-패턴--lock-충돌-폭발-2026-05-04) — 2026-05-04
- [실측 e2e 발견 — Supabase Storage 한글 key](#실측-e2e-발견--supabase-storage-한글-key-2026-05-06) — 2026-05-06
- [실측 e2e 발견 — schema migration 적용 필수](#실측-e2e-발견--schema-migration-적용-필수-2026-05-06) — 2026-05-06

### UX / Frontend
- [디자인 토큰 sweep ROI — UX Refactor 후속](#디자인-토큰-sweep-roi--ux-refactor-후속-2026-05-06) — 2026-05-06
- [React 컴포넌트 prop 타입 확장 — Polish P3](#react-컴포넌트-prop-타입-확장--polish-p3-2026-05-06) — 2026-05-06
- [DataTableShell 모바일 자동 변환 + vitest 텍스트 매칭 충돌](#datatableshell-모바일-자동-변환--vitest-텍스트-매칭-충돌--polish-p2-2026-05-06) — 2026-05-06

### Domain / Architecture
- [insane-search 어댑터 sanity 버그 + ranking 확장](#insane-search-어댑터-sanity-버그--ranking-확장-2026-07-06) — 2026-07-06
- [insane-search SERP 확장 — 통합검색/블로그탭/난이도 하이브리드](#insane-search-serp-확장--통합검색블로그탭난이도-하이브리드-2026-07-06) — 2026-07-06
- [insane-search 하이브리드 본문 fetcher 통합](#insane-search-하이브리드-본문-fetcher-통합-2026-07-06) — 2026-07-06
- [도메인 격리 유지 + DI 패턴 — `csv_parser.blog_resolver`](#도메인-격리-유지--di-패턴--csv_parserblog_resolver-2026-05-07) — 2026-05-07
- [FastAPI 라우트의 `status_code=204` + `-> None` 충돌](#fastapi-라우트의-status_code204---none-충돌-2026-05-07) — 2026-05-07
- [키워드 난이도 분석 속도 — Phase F 후속 튜닝](#키워드-난이도-분석-속도--phase-f-후속-튜닝-2026-05-04) — 2026-05-04
- [설계 결정](#설계-결정) — Phase 0.5/0.6 초기 결정 모음

### Operations / Process
- [Phase B9 마감 — todo.md 정합성 회복 패턴](#phase-b9-마감--todomd-정합성-회복-패턴-2026-04-29) — 2026-04-29
- [실수 패턴](#실수-패턴) — 일반 패턴 모음
- [실측 결과 (Phase 0.5)](#실측-결과-phase-05) / [Phase 0.6 (브랜드 카드)](#실측-결과-phase-06--브랜드-카드-트랙) — 부트스트랩 시점 검증 데이터 (참고용 보존)

---

## SEO 원고 파이프라인 교훈 (2026-04-16)

### [SEO-1] 분석 데이터가 프롬프트에 전달되지 않는 패턴

**증상**: 패턴 카드에 데이터가 있는데 최종 원고에 반영 안 됨.
**근본 원인**: `prompt_builder.py`가 유일한 전달 경로인데, 여기서 데이터를 누락하거나 왜곡.

발견된 케이스 4건:
1. **키워드 밀도 0.0000** — `cross_analyzer._range()`가 `round(0.002, 2)` = `0.00`으로 반올림. precision=4로 수정
2. **소제목 수 모순** — 분석 avg 0.9 → "소제목 1개"로 전달하지만 섹션 구조는 5개 요구. 섹션 수 기반 보정 로직 추가
3. **소구 포인트 빈 배열** — appeal 분석에서 `c >= 2` 임계값이 너무 높아 공통 포인트 0개. `most_common(5)`로 완화
4. **태그 0개** — 모바일 HTML에 태그 영역 없어 수집 불가. 키워드 기반 폴백 8개 추가

**교훈**: 분석 데이터를 프롬프트에 넣을 때 반드시 "이 값이 0이거나 빈 배열이면 어떻게 되는가?" 확인. 빈 값 폴백 로직 필수.

→ CLAUDE.md "분석 데이터 → 생성 반영 규칙"으로 승격 완료

### [SEO-2] 이미지 삽입 누락 패턴

**증상**: outline에서 6개 이미지 프롬프트 생성, 6개 모두 생성 성공, 그런데 MD/HTML에 5개만 삽입.
**근본 원인 3건**:
1. `assembler.insert_images_into_text()`에서 섹션 번호 > heading 수일 때 `if` 조건으로 스킵
2. `_normalize_position()`이 "글 후반", "마지막" 등 한국어 위치를 매칭 못 함
3. compliance fixer가 본문을 수정하면서 이미지 마커가 있는 re-assemble 경로에서 이미지 손실

**교훈**: 이미지는 "생성 수 = 삽입 수" 무결성 체크가 필수. 초과 섹션은 문서 끝 삽입으로 폴백.

→ CLAUDE.md "이미지 삽입 무결성" 규칙으로 승격 완료

### [SEO-3] 톤 지시와 의료법 규칙 충돌

**증상**: "경험 공유 대화체"로 지시 → LLM이 "저도 한때..." 1인칭 체험기 작성 → 의료법 `first_person_promotion` 위반 반복 → 3회 초과 실패.
**근본 원인**: "경험을 공유하듯" 지시를 LLM이 "나의 경험을 공유"로 해석. 1인칭 금지 규칙과 충돌.
**해결**: "친근한 전문가 톤"으로 변경. 1인칭(저는/제가) 명시적 금지 추가.

**교훈**: 톤 지시를 줄 때 의료법 금지 사항과 충돌하지 않는지 반드시 교차 검토. "경험"이라는 단어가 LLM에게 1인칭을 유도할 수 있음.

### [SEO-4] 물리 분석 정확도 — 네이버 HTML 파싱

**증상**: 키워드 횟수 0, 소제목 0, 문단 평균 658자.
**근본 원인**:
1. 키워드 "부천 다이어트 한의원" (공백)으로 검색하는데 본문에는 "부천다이어트한의원" (붙여쓰기)
2. `se-fs-fs{N}` 폰트 크기 패턴이 실제 HTML에 없음 (`se-fs-`만 존재)
3. `se-text` 컴포넌트를 1문단으로 처리해 비현실적 평균

**교훈**: 네이버 HTML 파싱은 반드시 실측 HTML fixture로 regression 테스트. 새 업종 테스트 시 물리 분석 결과를 먼저 눈으로 확인하고 진행.

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase 0.5/0.6 실측 결과 — 부트스트랩 시점 1회성 데이터, SPEC 반영 완료) -->

## 설계 결정

### AI 이미지 인물 정책 — 한국인 한정 허용 (2026-04-16)

**결정**: 사람·얼굴·실사 인물 사진을 모두 허용. 단, prompt 에 인물 키워드가 등장하면 반드시 `Korean` 명시.

**이유**: SEO 블로그에서 라이프스타일 사진(요가, 식사, 산책 등)이 핵심 노출 신호. 무조건 금지하면 이미지 품질·자연스러움이 떨어진다. 외국인 외형은 한국 콘텐츠 맥락과 어긋나므로 한국인으로 통일.

**유지되는 금지** (인물 유무 무관 영구):
- 환자 묘사 (`patient`, `환자`, `injured`)
- 전후 비교 (`before/after`, `weight loss progression`)
- 시술 장면 (`medical procedure`, `surgery`, `injection`)
- 신체 비교 (`body comparison`, `naked`)
- 효과 보장 (`100%`, `guarantee`)

**구현**: 
- `validate_prompt()` 가 사람 키워드 (`person`, `people`, `man`, `woman`, `face`, `portrait`, `family`, `child`) 감지 시 `Korean` 동반 확인
- 누락 시 fixer 가 `Korean` 자동 보강
- [6] outline LLM 프롬프트에 "인물 시 `Korean` 명시" 강제 주입
- 권장 시나리오에 한국적 라이프스타일 (한식, 한방, 한국 자연 등) 우선

**텍스트 금지는 불변**: Gemini 가 한글을 깨뜨리므로 모든 prompt 에 `no text`/`no letters` 항상 필수.

### Bright Data — SERP API 대신 Web Unlocker 단일 zone (2026-04-15)

**발견**: Bright Data SERP API 는 전용 파서를 제공하는 검색 엔진이 Google / Bing / Yandex / Baidu 로 한정되어 있고 **Naver 는 지원하지 않는다** (대시보드의 검색 엔진 드롭다운에 Google 만 노출).

**결정**: SERP 수집과 본문 수집을 모두 **Web Unlocker 단일 zone** 으로 처리한다.
- Web Unlocker 는 범용 fetcher 이므로 네이버 검색 결과 페이지 (`search.naver.com/search.naver?query=...&where=blog`) 도 그대로 fetch 된다
- 응답 HTML 을 BeautifulSoup 으로 직접 파싱해 블로그 URL 리스트 추출
- 본문 수집은 동일 zone 으로 블로그 URL 호출
- SERP API 의 구조화 JSON 파싱 기능은 어차피 필요 없으므로 손실 없음

**영향**:
- `config/.env`: `BRIGHT_DATA_SERP_ZONE` 제거, `BRIGHT_DATA_WEB_UNLOCKER_ZONE` 단일 사용
- `config/settings.py`: `bright_data_serp_zone` 필드 제거
- SPEC-SEO-TEXT.md §3 [1] 업데이트 (Web Unlocker + BS4 파싱으로 전환)
- crawling 스킬 업데이트

**재발 방지**: 서드파티 API 의 전용 지원 목록을 SPEC 착수 전 반드시 확인한다. "이 서비스에서 X 기능이 있다" 와 "우리 대상 서비스에 X 기능이 작동한다" 는 별개.

## 실수 패턴

### Supabase `public` 스키마 리셋 후 권한 누락 (2026-04-15)

**증상**: `service_role` 키로도 `permission denied for table X` 에러 (42501)

**원인**: `drop schema public cascade; create schema public;` 후 `grant usage on schema public to ...` 만 복원하고, **테이블 레벨 권한과 default privileges 복원을 빼먹음**. 그 결과 서비스 역할에 새 테이블 접근 권한이 없음.

**해결**: `config/schema.sql` 실행 시 다음을 함께 수행
```sql
grant all on all tables in schema public to postgres, anon, authenticated, service_role;
grant all on all sequences in schema public to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to postgres, anon, authenticated, service_role;
-- ...
```

**재발 방지**: `config/schema.sql` 하단에 GRANT/ALTER DEFAULT PRIVILEGES 구문을 항상 포함한다. public 스키마 리셋 절차는 Supabase 공식 예시를 따른다.

### 신규 도메인 등록 시 architecture-check STAGE_ORDER 동시 갱신 (2026-04-24)

**증상**: 신규 도메인 추가 후 `architecture-check.sh` 가 "알려지지 않은 도메인" 으로 차단

**해결**: `.claude/hooks/architecture-check.sh` 의 `STAGE_ORDER` 배열에 신규 도메인 등록 필수.
파이프라인과 무관한 격리 도메인은 0 으로 두고 다른 도메인을 import 하지 않는 방식이 안전 (예: `[ranking]=0`).

**재발 방지**: 새 `domain/X/` 디렉토리 생성 시 STAGE_ORDER 갱신을 todo.md 의 첫 task 로 둔다.

### `BLOG_POST_URL_RE` 의도적 복제 — 동기화 책임 (2026-04-24)

**상황**: `domain/ranking/url_match.py` 가 `domain/crawler/serp_collector.BLOG_POST_URL_RE` 와 동일한 정규식을 의도적으로 복제.

**이유**: 도메인 격리 원칙 (`domain/ranking → domain/crawler` import 금지). DI 패턴으로 SERP fetch/parse 는 application 이 합성하지만 정규식 자체는 복제가 합리적.

**위험**: 한쪽 변경 시 다른 쪽 누락 → 매칭 미스로 SPEC-RANKING.md §11 R1 위험.

**완화**:
1. 양쪽 파일 상단 주석에 "의도적 복제, 동기화 필수" 명시
2. `tests/test_ranking/test_url_match.py::TestRegexCopySync::test_pattern_string_identical` 가 패턴 문자열을 자동 비교 (분기 시 즉시 실패)

**재발 방지**: serp_collector 의 정규식을 수정할 때는 무조건 url_match 도 같이 수정. 위 자동 비교 테스트가 1차 방어.

### Ranking Tracker — 멀티 인스턴스 advisory lock 필수 (2026-04-24)

**상황**: SPEC-RANKING.md §10 8 — APScheduler in-process 가 매일 09:00 KST cron job 실행. **단일 인스턴스 전제**.

**위험**: render.yaml 을 free → paid (수평 확장) 또는 다른 클라우드 멀티 인스턴스 배포 전환 시 각 인스턴스의 APScheduler 가 동시에 동일 잡 실행 → SERP 호출 N배, ranking_snapshots 중복 insert.

**완화 (전환 시점에 적용)**:
- Supabase 에 advisory lock 테이블 추가 (`ranking_check_locks(date pk, locked_at, owner)`)
- `_run_daily_check()` 시작 시 `INSERT ... ON CONFLICT DO NOTHING` 으로 그날 락 획득 시도. 실패하면 즉시 종료
- 또는 Redis 분산 락 (운영 인프라가 더 큰 경우)

**재발 방지**: render.yaml 또는 배포 설정에 인스턴스 수 변경 시 본 메모를 확인하고 advisory lock 추가 PR 을 함께.

### pytest 전체 실행 시 출력 버퍼링 + 커버리지 cold start (2026-04-28)

**증상**: `pytest -q 2>&1 | tail -8` 호출 후 15분간 출력 0 라인 → hang 으로 오해. 강제 stop 후 재시도 반복으로 cache 무효화 → 더 느려짐. 사용자가 "언제 끝나니?" 두 번 묻는 상황까지 발전.

**근본 원인 2건 결합**:
1. **bash 파이프 출력 버퍼링** — `| tail -N` 은 입력 스트림을 EOF 까지 읽어야 출력. pytest 의 진행 도트(`.`)는 흐르고 있으나 화면에 안 보임. 로그 파일도 0 바이트 (FD flush 가 tail 종료 시점)
2. **`pyproject.toml` 의 `--cov` 강제** — 800개 테스트 × 5,573 statement 인스트루먼트, cold start 시 매우 느림. 이전 build-check.sh 56초는 hot cache 였음

**재발 방지 — pytest 실행 표준**:
- ❌ 금지: `pytest ... 2>&1 | tail -N`
- ✅ 출력 직접 보기: `pytest -q --no-cov` (line-buffered, 도트 실시간)
- ✅ 출력 잘라야 한다면 `tee` 로 분기: `pytest -q --no-cov 2>&1 | tee /tmp/pytest.log | tail -20`
- ✅ 빠른 반복: `--no-cov` 로 인스트루먼트 끔. 커버리지 게이트는 build-check.sh 한 번만
- ✅ 부분 회귀: 변경 영향 모듈만 명시 (`pytest tests/test_brand_card --no-cov` 등). 798 → 298 으로 줄어 2.4초
- ✅ Hang 의심 시 stop 보다 로그 파일 직접 read 가 우선 (불필요한 cache 무효화 방지)

**교훈**: bash 파이프 + heavy instrumentation 조합은 사일런트 진행으로 보인다. "출력 없음 = 진행 없음" 추론 금지.

---

## Phase B9 마감 — todo.md 정합성 회복 패턴 (2026-04-29)

todo.md 의 Phase 1 부터 Phase B9 까지 다수 체크박스가 stale 이었다. 실제로는:
- SEO 트랙 Phase 2~8: 모두 구현·검증 완료, 체크박스만 ROADMAP 형태 ("각 단계 착수 시 분해" 주석)
- 브랜드 카드 트랙 Phase B1~B8: 거의 다 구현. SPEC 명명과 실제 파일명이 통합·재구성됨
  - `repository.py` → `storage.py`
  - `card_planner.py` → `plan_generator.py`
  - `image_generator.py` → `image_prefetch.py`
  - `source_loader.py` → `source_parser.py`
  - `asset_extractor.py` + `asset_merger.py` → `asset_merge.py` 통합
  - `playwright_renderer.py` + `html_renderer.py` → `renderer.py` 통합
- Phase B7 의 9000px 분할/PNG tEXt 메타/hard max 18000 3건은 SPEC v2 P1 제외 (long-form, P2). lessons BC-7 의 SPEC §2-4 보완 노트는 v1 시절 잔재
- "사용자 제공 대기 중" 의 의료법 카테고리 / 5번째 템플릿도 stale

**Phase B9 완료**:
- `application.orchestrator.run_full_package` — ThreadPoolExecutor(2) 병렬 + 한쪽 예외가 다른 쪽 종료시키지 않는 격리 패턴 (`future.result()` 를 try/except 로 개별 감싸 결과 보존)
- `run_brand_card_only(auto_approve=False)` 가 [B5] 까지만 (draft 게이트), `True` 면 [B12] 까지 (E2E·자동화). 사용자 승인 게이트는 `auto_approve` 단일 플래그로 토글
- `PackageResult.status` 결정 규칙: 둘 다 SUCCEEDED → SUCCEEDED, 둘 다 FAILED → FAILED, 한쪽이라도 SUCCEEDED → SUCCEEDED (부분 성공). `error` 필드에는 두 트랙 예외 메시지를 `; ` 로 합침
- scripts CLI 4종은 모두 얇은 argparse 래퍼. `register_brand` / `remove_media` 는 application 진입점을 거치지 않고 `domain.brand_card.storage` 의 CRUD 함수를 직접 호출 (인프라 작업이라 스테이지/리포터 불필요)

**교훈**:
1. todo.md 체크박스가 ✅ 마킹 없이 미완료로 보여도 실제 코드를 먼저 확인. SPEC 명명 vs 파일명 차이는 "통합" 으로 자연스럽게 발생
2. ThreadPoolExecutor 병렬 실행 시 `future.result()` 는 반드시 개별 try/except 로 감싸야 한쪽 예외가 다른 트랙 결과 손실로 이어지지 않는다
3. `auto_approve` 플래그처럼 게이트를 토글로 둘 때, 디폴트는 사람의 승인 (False) 이어야 안전. E2E·자동화에서만 True
4. SPEC v 변경(v1 long-form → v2 인스타 카드) 시 lessons.md 의 옛 측정 노트도 SPEC 영역에 따라 P1/P2 재분류 필요. 자동 마이그레이션 안 됨

## Vercel 함수 페이로드 4.5MB 한계 — Presigned URL 우회 (2026-04-30)

**증상**: 브랜드 sources 첨부 업로드 시 PDF/DOCX 등이 `API 413: FUNCTION_PAYLOAD_TOO_LARGE icn1::...` 로 실패.

**근본 원인**: Vercel Serverless Function 의 요청 본문 한계는 **4.5 MB hard limit** (hobby/pro 동일, 변경 불가능). Vercel proxy(`web/frontend/src/proxy.ts`) 가 X-API-Key 주입 후 `next.config.ts` rewrites 로 백엔드 origin 에 전달하는 구조라, 멀티파트 본문이 Vercel 함수 단에서 컷.

**해결**: Supabase Storage **presigned PUT URL 패턴** (옵션 A).
- 백엔드 `/sources/init` 가 signed URL 발급 (작은 JSON, < 1KB → Vercel 한계 무관)
- 브라우저가 Supabase Storage 도메인으로 **직접 PUT** (Vercel 우회)
- `/sources/confirm` 이 다운로드 + sha256 재검증 + parser → DB INSERT
- 검증 게이트: `storage_path = {brand_id}/sources/{sha256}{suffix}` 정확 일치 (path traversal 방어), 다운로드 본문 sha256 = req.sha256 (변조 방어)

**교훈**:
1. **호스팅 한계는 코드로 우회 불가능**. Vercel 함수 한계처럼 외부 인프라 제약은 아키텍처 (직접 PUT, 외부 스토리지) 로 우회. Edge runtime 으로 바꿔도 4.5MB 한계는 그대로
2. **3단계 흐름의 검증 게이트**: storage_path 패턴 검증 + sha256 재검증 두 개가 모두 있어야 안전. path 만 보면 변조, sha256 만 보면 임의 경로 업로드 가능
3. **`crypto.subtle.digest("SHA-256")`** 는 표준 WebCrypto API — 모든 모던 브라우저 지원, polyfill 불필요
4. **Supabase signed URL 응답 키** 는 SDK 버전에 따라 `signedURL`/`signed_url` 혼재 — 양쪽 폴백 필요 (`storage_signed._extract_signed_upload`)
5. **CORS 설정 빠뜨리면 PUT 실패** — Storage 버킷별 CORS 에 운영 도메인 + localhost:3000 추가 필수

## In-process APScheduler + 단일 컨테이너 = cron 누락 함정 (2026-05-03)

**증상**: 매일 09:00 KST 자동 발화하던 ranking_snapshots 가 **2026-04-30 / 05-01 두 날만 0건** (인접 4/29 105건, 5/2 48건). `api_usage` 테이블에도 stage='ranking_check' row 0건 — cron 자체가 미발화.

**진단 과정의 함정**:
1. 처음엔 "log silent" 가설 — `web/api/main.py` 에 `logging.basicConfig` 가 없어 `logger.info(...)` 가 root WARNING 에 막혀 안 보임을 확인. 하지만 Supabase row 0건 사실로 가설 기각 (cron 진짜 미발화).
2. Render Events 의 OOM/restart 와 cron 시각이 어긋난 게 진짜 원인. 단일 컨테이너 Starter (512MB) + brand-card Playwright 트래픽 → OOM-kill → APScheduler in-memory jobstore 가 매 재시작마다 0 으로 초기화 → `coalesce=True` 도 무용.

**핵심 함정**:
- `coalesce=True` 는 "스케줄러가 살아있는 동안 놓친 1회 보충" 의미. **재시작으로 jobstore 가 휘발되면 missed-run 기록 자체가 사라져 보충 안 됨.**
- AsyncIOScheduler 를 lifespan 에서 시작하는 구조는 컨테이너 lifecycle 과 강결합. PaaS 의 OOM-kill / 자동 패치 / deploy 가 곧 cron 누락.

**해결 — 외부 cron 분리**:
1. `POST /api/rankings/check-all` (X-API-Key + BackgroundTasks + threading.Lock 동시실행 가드)
2. `.github/workflows/ranking-cron.yml` 매일 09:00 KST 호출, `--retry 3 --retry-delay 60`, 실패 시 GitHub Issue 자동 생성
3. `ranking_scheduler_enabled` default `False` — APScheduler 코드는 로컬 개발용으로만 잔존
4. `logging.basicConfig(INFO)` — uvicorn 이 root logger 를 WARNING 으로 두는 문제 동시 해결 (다음 사고 진단 가속)

**일반화 가능한 규칙**:
- **PaaS 단일 컨테이너 + in-memory state 로 cron 을 운영하지 말 것**. 외부 트리거(GitHub Actions / Render Cron / cron-job.org / Supabase pg_cron) 가 누락 0 보장.
- **silent failure 방지** — 외부 cron 은 실패가 UI 에 빨간불로 보이지만 in-process 는 로그로만 알 수 있음. 그 로그조차 root logger 미설정으로 silent 가능.
- **로깅은 진단의 전제** — `logging.basicConfig` 없는 FastAPI 앱은 application logger.info 가 stdout 에 안 찍힘. uvicorn 자체 logger 만 출력.

## save_usage_to_supabase silent failure + 자동 검증 (2026-05-03)

**증상**: 2026-05-02 KST 09:00~09:06 측정 사이클의 ranking_snapshots 48 건은 정상 INSERT, 같은 사이클 api_usage 0 건. dashboard 일별 추이 5/2 통째 누락. Render Logs 도 그 시간대 침묵 (외부 origin) — 다만 같은 패턴이 컨테이너 내에서 발생해도 silent 였을 구조.

**근본 결함**: `save_usage_to_supabase` 의 `try/except: logger.error + return False` 패턴에서 (1) 호출자가 반환값 무시 (2) ERROR 로그가 row 수·exception type·sample 없이 빈약 (3) Supabase 일시 장애 흡수용 retry 부재. 셋이 결합돼 데이터가 silent 로 사라짐.

**해결 — 4 단계 보강** (PR `feat(usage-guard)` 2026-05-03):
1. `save_usage_to_supabase` 자체에 tenacity exponential backoff (1s/2s/4s, 3 시도) + ERROR 로그에 `row_count` + `exc_type` + `first_row_provider` + `first_row_keyword` 명시
2. caller 가 결과 인지 — `check_rankings_for_publication` 가 False 받으면 module-level threading.Lock counter +1 + WARNING 로그
3. summary 노출 — `RankingCheckSummary.usage_save_failed_count` 신규 필드 + check_all 종료 시 0 보다 크면 logger.warning
4. 외부 자동 검증 — `GET /api/rankings/check-all/last` 폴링 endpoint + GitHub Actions workflow 가 15s × 100 회 polling 으로 status='succeeded' + errors_count==0 + usage_save_failed_count==0 까지 확인. 어긋나면 workflow fail + GitHub Issue 자동 생성

**일반화 규칙**:
- **silent failure 가능한 모든 외부 IO 는 결과를 caller 까지 전달**. bool 반환만으론 부족 — 카운터 또는 named result 객체로 누적
- **retry 가 빠진 외부 IO 는 일시 장애에서 데이터를 잃음**. tenacity stop_after_attempt(3) + exponential backoff 가 최소 표준
- **자동 검증 없는 cron 은 사고 후에야 발견**. 결과 polling endpoint + workflow 카운터 검사가 가장 가벼운 안전장치
- **ERROR 로그는 사후 진단에 필요한 모든 컨텍스트를 한 줄에**: row 수, exception type, 식별 가능한 sample. `exc_info=True` 만 의존 X

## Mutating endpoint 에 외부 retry 거는 패턴 = lock 충돌 폭발 (2026-05-04)

**증상**: GitHub Actions `ranking-daily-check` 가 빨간불. 로그:
```
curl: (28) Operation timed out after 60002 milliseconds with 0 bytes received
curl: (22) The requested URL returned error: 409
curl: (22) The requested URL returned error: 409
curl: (22) The requested URL returned error: 409
```

**시퀀스 분석**:
1. 첫 `POST /check-all` 60s timeout (Render cold start 또는 lifespan startup 지연)
2. 백엔드는 요청을 받아 `_check_all_running=True` 설정 + BackgroundTasks 등록
3. curl `--retry 3 --retry-all-errors` 가 timeout 도 retry 대상으로 동일 POST 재전송
4. lock 잡힌 상태 → 우리 endpoint 가 409 반환
5. 3번 모두 409 → workflow exit 22

**근본 결함**:
- `POST /check-all` 은 **lock 보유 = 멱등 아님**. 그런데 외부에서 retry 거는 게 안티패턴
- `--fail-with-body` 는 첫 호출 실패만으로 workflow 빨간불. 실제로는 백엔드가 BackgroundTasks 로 측정을 정상 진행했을 수도
- 검증은 별도 step 이 `/check-all/last` polling 으로 하는데도 첫 호출 결과가 fail 판정의 근거가 됨

**해결 — 양쪽 다 패치**:
1. **Endpoint 자체를 idempotent 하게**: 이미 실행 중이면 409 → **200 + `{status: "already_running", started_at: ...}`**. retry 가 와도 안전. 외부 retry 전략 무엇이든 lock 충돌 0.
2. **Workflow 의 retry 제거 + max-time 늘림**: `--retry`, `--retry-all-errors`, `--fail-with-body` 모두 제거. `--max-time 120` 으로 cold start 흡수. 첫 호출 실패해도 exit 0 유지. 진짜 판정은 다음 step 의 `/check-all/last` polling 이 책임.

**일반화 규칙**:
- **Mutating endpoint (POST/PUT/DELETE) 에 외부 retry 거는 건 안티패턴**. retry 하려면 endpoint 자체를 idempotent 하게 만들 것 (lock 잡힌 상태도 200 + 진행 정보)
- **`--fail-with-body` + retry 조합은 첫 호출 실패만으로 workflow 빨간불**. mutating endpoint 면 첫 호출 결과를 fail 판정 근거로 쓰지 말고, 별도 polling step 으로 진짜 결과를 확인
- **Cold start 흡수는 timeout 으로**, retry 가 아니라. POST 는 timeout 늘리고 GET 만 retry 거는 게 안전
- **idempotency key 또는 idempotent 응답 — 둘 중 하나는 mutating endpoint 의 표준**. 외부 호출 (cron, webhook, queue) 에서 호출되는 endpoint 는 특히

## 키워드 난이도 분석 속도 — Phase F 후속 튜닝 (2026-05-04)

**배경**: F1~F4 적용 후 50키워드 ~50초. 추가 단축 여지 분석 결과 병목은 **BrightData SERP fetch (5~8초/건)**. lxml 은 이미 적용 완료. 즉시 적용 가능한 4가지를 한 PR 로 묶음.

**1단계 변경** (즉시 효과):
- `BRIGHT_DATA_BATCH_PARALLEL` 8 → 12 (env, settings 동적)
- `BRIGHT_DATA_BATCH_RATE_SECONDS` 0.3 → 0.2
- UI 청크 8 → 4 (첫 결과 ~3초 안에 표시)

**2단계 변경** (캐시 적극 활용):
- SERP 캐시 TTL 30분 → 60분 (`KEYWORD_DIFFICULTY_CACHE_TTL_SECONDS`)
- 매 hit/miss 마다가 아니라 **50회 이벤트마다 1줄 stats 로그** — `serp_cache.stats hits=N misses=M hit_ratio=X% size=K ttl_sec=T`
- 운영 1주일 후 hit_ratio 보고 TTL 추가 상향 결정 (2~6시간 시도 가능)

**일반화 규칙**:
- **속도 튜닝 상수는 settings 로 빼서 운영 중 env 로 보정**. 코드 배포 없이 hotfix 가능. 4xx 폭발 시 `BRIGHT_DATA_BATCH_PARALLEL=4` 즉시 하향
- **로그는 매 호출마다 찍지 말고 누적 통계 주기적으로**. 매 hit 마다 INFO 가 찍히면 운영 로그 노이즈 + 진단 어려움. 50회마다 1줄이 적정
- **UI 체감 속도 ≠ 백엔드 처리 시간**. 청크 작게 + 첫 결과 즉시 표시가 사용자 경험에 더 큼. 백엔드는 12 동시도 충분

---

## 디자인 토큰 sweep ROI — UX Refactor 후속 (2026-05-06)

**배경**: UX Refactor 6 Phase 종료 후 287 위치 / 50+ 파일에 색상 클래스 (`bg-red-50`, `bg-amber-100` 등) 산발. "전체 sweep" 충동 vs "의미 매핑 가능한 것만" 간 결정.

**시도**: Polish Pack P1 에서 StatusBadge 만 (35 위치) 토큰화. 이후 B1 작업으로 287 위치 추가 분석.

**결과**: 7 파일 53 위치를 분류하니 실제 의미 매핑 가능한 것은 **ComplianceRiskBadge (7) + JobList (4)** 만. 나머지는:
- Button: brand color (variant 자체가 의미)
- PublicationStatusBadge: 5-stage lifecycle 자체 의미
- BatchProgressTable: progress bar 강한 색
- BatchReviewQueue / HoldDialog / BulkRegisterDialog: brand action color
- 페이지 직접 사용분 (운영 홈 SummaryCards / 키워드 차트 등): 페이지 고유 의미

**일반화 규칙**:
- **토큰 sweep 가치 = 의미 매핑 가능한 위치 수 ÷ 전체 위치**. 10% 미만이면 sweep 보다는 **분류 + 명확한 OUT-OF-SCOPE** 가 효율적
- **brand color (primary blue)** 는 status token 과 분리 — 변경하면 브랜드 정체성 영향
- **lifecycle 자체 의미** 를 가진 컴포넌트 (5-stage indicator 등) 는 별도 token 계열 추가 vs raw 유지 결정 필요. 운영 데이터 누적 후 다크모드 도입 시 통합
- **287 위치 강제 sweep 강요는 금물** — 의미 부적합 위치를 token 으로 끼워맞추면 다크모드/리브랜딩 시 더 큰 부채

---

## Windows cp949 콘솔 + Python 한글 처리 — Polish P4 (2026-05-06)

**배경**: `kiwipiepy` (한국어 형태소 분석) 도입 후 build-check.sh 의 pytest 가 한글 string 처리 시 실패. `.venv/Scripts/python.exe -m pytest` 직접 호출은 통과, build-check 의 `pytest` 는 fail.

**원인 발견**:
- `which pytest` → `/c/Users/assag/AppData/Local/Programs/Python/Python313/Scripts/pytest` (system Python)
- system Python 에 kiwipiepy 미설치 → ImportError → fallback (False) → 4 케이스 fail
- `.venv` 의 pytest 와 다른 인터프리터 사용 중

**해결**:
1. `pip install kiwipiepy>=0.17` 을 system Python 에도 적용 (사용자가 venv activate 안 하고 build-check 직접 호출하는 환경 가정)
2. build-check.sh 의 pytest 호출에 `env PYTHONUTF8=1 PYTHONIOENCODING=utf-8` prefix 추가 (cp949 default 회피)

**일반화 규칙**:
- **Windows + Python 의 default encoding 은 cp949** (한국어 locale). Python 3.7+ 의 `PYTHONUTF8=1` 이 가장 강력한 해결책
- **build-check 같은 hook 스크립트는 venv activate 가정 X** — 사용자가 어느 환경에서 호출하든 같은 결과 보장 필요. 명시적 PATH 또는 환경 변수 prefix
- **system Python vs .venv 충돌** 가능성 — `which pytest` 로 사전 점검. 본 프로젝트는 양쪽 모두 의존 설치 권장 (또는 .venv activate 강제 hint)
- **kiwipiepy 형태소 분리 모호성**: 같은 단어 ("한의원") 가 컨텍스트에 따라 다르게 분리됨 (`["한의원"]` vs `["의원"]`). set 교집합 대신 **substring 매칭** (`noun in title_lower`) 으로 회피하면 분리 결과 의존성 제거 + 더 강건

---

## React 컴포넌트 prop 타입 확장 — Polish P3 (2026-05-06)

**배경**: PageHeader 의 `title: string` prop 에 HelpTooltip 같은 inline ReactNode 삽입 필요. 두 가지 옵션 — title 옆에 별도 prop 추가 vs `title` 타입 자체 확장.

**시도**: title 타입을 `string` → `ReactNode` 로 확장. h1 의 className 도 `flex items-center` 추가해 inline 노드 정렬.

**결과**: 모든 호출자가 자연스럽게 `<>...<HelpTooltip /></>` 패턴 사용. 별도 prop 없이 깔끔.

**일반화 규칙**:
- **inline 노드 가능성 있는 prop 은 처음부터 `ReactNode` 권장** — 단순 string 으로 시작했다가 Node 로 확장하는 경우 잦음. 초기에 `ReactNode` 면 호환성 유지
- **flex items-center 컨테이너 권장** — inline 노드 (icon, badge, tooltip) 가 들어올 때 정렬 깨짐 방지

---

## DataTableShell 모바일 자동 변환 + vitest 텍스트 매칭 충돌 — Polish P2 (2026-05-06)

**배경**: DataTableShell 에 모바일 카드 + 데스크톱 테이블 양쪽 마크업을 동시 렌더 (`md:hidden` / `hidden md:block`). 기존 vitest 의 `getByText("이름")` 이 양쪽에 매칭되어 unique 실패.

**해결**: vitest 가 desktop `<th>` 만 명확히 클릭하도록 `container.querySelector("th")` 사용. `getByText` 대신 DOM 위치로 매칭.

**일반화 규칙**:
- **반응형 양쪽 렌더링 (md:hidden + hidden md:block) 패턴** 도입 시 기존 vitest 의 텍스트 매칭이 양쪽 매칭으로 깨짐. 사전 grep `getByText|getAllByText` 로 영향 평가
- **DOM 위치 기반 매칭** (`querySelector("th")`, `getAllByText()[0]`) 가 vitest 의 `getByText` 보다 모호성 적음. 단 selector specificity 유지 필요
- **jsdom 의 viewport 한계**: `md:hidden` 같은 Tailwind 분기는 className 으로 hidden 표현 — DOM 에는 모두 존재. matchMedia mock 으로도 className 기반 hidden 은 우회 안 됨

---

## 실측 e2e 발견 — Supabase Storage 한글 key (2026-05-06)

**배경**: UX Refactor + Polish Pack 후 정적 e2e (코드 path 검증) 통과. 그러나 실측 e2e (`python scripts/run_pipeline.py --keyword "다이어트한의원"`) 에서 발견:

```
StorageApiError: Invalid key: 다이어트한의원/20260506-143336/images/image_10.jpg
```

**원인**: `application/stage_runner._storage_prefix()` 가 `output_dir.parent.name` (한글 키워드 그대로) 를 Storage key 에 사용. Supabase Storage 는 ASCII-safe key 만 허용 (percent-encoded URL 도 InvalidKey reject).

**해결**: `_ascii_safe_slug(name)` helper 신규. 영문/숫자/하이픈/밑줄/점만 보존, 그 외 (한글 등) 는 SHA1 short hash 12자 → `kw-{hash}` 형식.

**일반화 규칙**:
- **외부 시스템 (Storage / 외부 API URL) 의 key 는 ASCII-safe 강제** — 한글 등 비-ASCII 는 hash 또는 transliteration 으로 변환
- **percent-encoding 만으로 안 통과** — Supabase Storage 는 raw key 검증
- **deterministic hash** (SHA1[:12]) — 같은 키워드는 같은 prefix, 운영 도구 reverse lookup 가능
- **로컬 path (`output/{keyword}/`) 는 그대로 유지** — 사용자 가독성 우선, Storage upload 시점에만 변환

---

## 실측 e2e 발견 — schema migration 적용 필수 (2026-05-06)

**배경**: 같은 e2e 실행에서:

```
APIError: Could not find the 'job_id' column of 'generated_contents'
```

**원인**: `config/schema.sql` 에 `generated_contents.job_id` 컬럼 + index + alter 정의 (line 34/49/215~218) 되어 있으나, 운영 Supabase 에 SQL 미적용.

**해결**: 사용자 manual 적용 — `config/schema.sql` 의 alter 블록 (line 215~221) 을 Supabase SQL Editor 에서 실행.

**일반화 규칙**:
- **schema.sql 변경 후 Supabase Editor 적용은 manual** — 자동화 안 됨. 변경 commit 시 README/release note 에 명시
- **APIError 의 `Could not find the 'X' column'` 패턴**: 100% schema 미적용 신호. 코드 변경 X, SQL 적용만 필요
- **graceful fallback 유무**: `_save_generated_to_supabase` 가 `try/except` 로 감싸 fail 시 logger.warning 만 (파이프라인 중단 X) — 정상 동작. UI 가 Supabase 데이터 의존하면 외부 진입 불가하지만 결과 자체는 로컬 보존됨
- **e2e 검증의 가치**: 정적 코드 검증으로 못 잡는 **운영 환경 의존성** (Storage key 제약, schema 적용 여부) 을 1회 키워드로 자연 발견 가능

---

## 도메인 격리 유지 + DI 패턴 — `csv_parser.blog_resolver` (2026-05-07)

**배경**: Blog Channels Phase 1 구현 시 `domain/batch/csv_parser.py` 가 CSV 의 `blog` 컬럼 raw 텍스트(별칭 또는 네이버 blog_id) 를 `blog_channel_id` 로 변환해야 했다. 단순한 해결책은 `from domain.blog_channel import storage` 를 import 해 lookup 하는 것.

**문제**: `architecture-check.sh` 의 `STAGE_ORDER[batch]=0` (격리 도메인) 위반 — domain 간 직접 import 금지 룰. 격리 룰을 우회해 만들면 6개월 뒤 다른 도메인 간 import 가 자연스럽게 늘어나면서 dependency hell.

**해결**: **DI 패턴**. `parse_csv` 가 `Callable[[str], str | None]` 타입의 `blog_resolver` 옵션 인자를 받는다. csv_parser 자체는 blog_channel 도메인을 알 필요가 없다.

```python
# domain/batch/csv_parser.py — 도메인 격리 유지
BlogResolver = Callable[[str], str | None]

def parse_csv(csv_text, *, batch_id, default_mode, blog_resolver=None):
    ...
    blog_channel_id = blog_resolver(blog_raw) if blog_resolver and blog_raw else None

# application/batch_orchestrator.py — 합성 책임
def _build_blog_resolver() -> csv_parser.BlogResolver | None:
    channels = blog_channel_storage.list_channels(limit=500)
    by_name = {c.name.strip().lower(): c.id for c in channels if c.id}
    by_blog_id = {c.blog_id.strip().lower(): c.id for c in channels if c.id}
    return lambda raw: by_name.get(raw.strip().lower()) or by_blog_id.get(raw.strip().lower())
```

**일반화 규칙**:
- **격리 도메인 (STAGE_ORDER=0) 이 다른 도메인 데이터를 필요로 할 때**: import 대신 함수 인자 (DI) 로 받는다
- **lookup 캐시는 application 레이어에서 1회 생성** — 매 row DB 호출 회피 (CSV 1000 row × 1 channels 호출 = 1000 round-trip)
- **resolver = None 폴백**: Supabase 미연결 환경 / cold start 시 raw 무시 + null 저장 → 운영 무영향
- **architecture-check.sh 의 격리 룰은 건드리지 않는다** — 룰을 비틀기 시작하면 다른 모듈도 따라 비틀린다

**참조**:
- `domain/batch/csv_parser.py:36~118`
- `application/batch_orchestrator.py:_build_blog_resolver`
- `tests/test_batch/test_csv_parser.py:test_blog_resolver_resolves_alias_and_id`

---

## FastAPI 라우트의 `status_code=204` + `-> None` 충돌 (2026-05-07)

**배경**: `web/api/routers/blog_channels.py` 에 DELETE 엔드포인트를 추가:

```python
@router.delete("/{channel_id}", status_code=204)
def delete_blog_channel(channel_id: str) -> None:
    ...
```

**증상**: 이 라우터를 import 하는 모든 web/api 테스트가 setup error.

```
AssertionError: Status code 204 must not have a response body
fastapi/routing.py:507: AssertionError
```

import 시점에 라우트 등록이 실패해서 `from web.api.main import app` 자체가 raise → 같은 fixture 를 쓰는 N개 테스트가 일제히 ERROR (개별 실행은 PASS — 헷갈림 포인트).

**원인**: FastAPI 가 `-> None` 반환 어노테이션을 "response body = None type" 으로 추론한다. status 204 (No Content) 는 정의상 body 가 없어야 하므로 라우트 등록 시 `assert is_body_allowed_for_status_code(status_code, response_model)` 실패.

**해결**: `Response` 객체를 직접 반환.

```python
from fastapi import Response

@router.delete("/{channel_id}")  # status_code 제거
def delete_blog_channel(channel_id: str) -> Response:
    ...
    return Response(status_code=204)
```

**일반화 규칙**:
- **FastAPI 의 204/304/1xx 등 body-금지 status**: `status_code=204` + `-> None` 조합 금지. `-> Response` + `return Response(status_code=...)`
- **개별 PASS / 전체 FAIL 패턴**: import 시점 raise 의 전형. 첫 ERROR 테스트의 traceback 에서 import 라인 (`web/api/main.py:18: in <module>`) 을 본다 — 단독 실행 시 같은 import 가 일어나지 않으면 캐시·다른 fixture 가 미리 모듈을 import 했을 가능성. `from web.api.main import app` fixture 를 쓰는 모든 router 테스트가 동시 fail 이면 라우트 등록 실패 의심

**참조**: `web/api/routers/blog_channels.py:delete_blog_channel`

---

## 테스트에서 SWR 캐시 격리 — `SWRConfig provider: () => new Map()` (2026-05-07)

**배경**: `PublicationForm.test.tsx` 에서 SWR 로 `listBlogChannels` 를 호출하는 컴포넌트 테스트 추가. `mockResolvedValueOnce` 로 채널 목록을 다르게 반환하려 했는데 두 번째 케이스가 첫 번째 케이스의 mock 결과를 그대로 받음.

**원인**: SWR 의 글로벌 캐시는 **테스트 모듈 인스턴스 전체에서 공유**된다. 첫 테스트에서 `K.blogChannels` 키로 캐시된 결과가 두 번째 테스트 render 시 즉시 hit → fetcher 미호출 → `mockResolvedValueOnce` 가 소비되지 않음.

**해결**: 각 테스트 wrapper 에서 `SWRConfig` 의 `provider` 를 새 Map 으로 주입.

```typescript
function withSwr(children: ReactNode) {
  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
}

// 사용
render(withSwr(<PublicationForm variant="create" />));
```

**일반화 규칙**:
- **SWR 의존 컴포넌트의 vitest 테스트**: 항상 `SWRConfig provider: () => new Map()` wrapper 로 감싼다 — 캐시 격리
- **`dedupingInterval: 0`** 도 함께 — 짧은 시간 안의 동일 키 호출이 합쳐지는 동작 회피 (테스트 setup ↔ act 가 같은 tick 일 수 있음)
- **`mockResolvedValueOnce` vs `mockResolvedValue`**: SWR 캐시 격리 후에도 fetcher 가 1번만 호출되리란 보장은 없음 (revalidation·focus 등). 안정성 우선이면 `mockResolvedValue` 로 일관 응답 + 케이스별로 다른 응답이 필요할 때만 cache 격리 + Once

**참조**: `web/frontend/src/components/__tests__/PublicationForm.test.tsx:withSwr`

---

## build-check.sh 의 pytest 는 system python 사용 — venv 와 의존 동기화 필수 (2026-05-08)

**배경**: UX Refactor Step 4 에서 kiwipiepy 를 venv 에 설치한 뒤 단독 pytest 실행은 32/32 PASS. 그러나 `build-check.sh` 의 전체 pytest 는 5 fail (TestNormalizeMorpheme 4 + TestKeywordRepetitionMorphemeBranch 1).

**원인**: `build-check.sh` 가 `pytest -q` 만 호출 → `which pytest` 가 `/c/Users/assag/AppData/Local/Programs/Python/Python313/Scripts/pytest` (시스템 python) 을 가리킴. venv 의 pytest 가 아님. 시스템 python 에는 kiwipiepy 미설치 → `_get_kiwi()` 가 ImportError → `_kiwi_unavailable=True` 모듈 글로벌 변수 set → 전체 morpheme 테스트 fail.

**해결**: 시스템 python 에도 kiwipiepy 설치.

```bash
/c/Users/assag/AppData/Local/Programs/Python/Python313/python.exe -m pip install "kiwipiepy>=0.17"
```

**일반화 규칙**:
- **`bash .claude/hooks/build-check.sh` 는 시스템 python 의 pytest 사용** — Windows 환경에서 venv 활성화 없이 호출되는 패턴. venv 와 시스템 python 양쪽에 같은 패키지 설치 필요
- **신규 의존 추가 시 두 번 설치**: `.venv/Scripts/python.exe -m pip install X` + 시스템 python 도 동일
- **단독 PASS / build-check FAIL 패턴 진단**: `which pytest` + `which python` 로 PATH 확인 → 시스템 vs venv 차이 의심
- **모듈 글로벌 캐시의 함정**: `_kiwi_instance` 같은 lazy singleton 이 첫 호출에서 ImportError 면 `_kiwi_unavailable=True` 가 모듈 lifetime 동안 유지. 한 테스트 fail 이 후속 테스트 전체 fail 유발. monkeypatch 만으로는 cleanup 안 됨 (글로벌 변수는 setattr 대상 아님)
- **장기 해결**: `.venv/Scripts/python.exe -m pytest` 로 build-check.sh 변경 (TODO — 운영 환경 고정 후)

**참조**:
- `domain/generation/title_validator.py:_get_kiwi` (singleton + ImportError sticky)
- `.claude/hooks/build-check.sh:64` (`pytest -q` 시스템 호출)

---

## In-memory JobManager 휘발 + 폴링 retry-bound 패턴 (2026-05-08)

**사고**: `/api/jobs/5886b339a0a1` 폴링이 502→503→404 100회 이상 누적. 사용자 브라우저가 분당 20회씩 의미 없는 트래픽 생성 + 진행 분실 사실 인지 불가.

**근본 원인**: `web/api/job_manager.JobManager._jobs` 가 **in-memory dict**. Render starter plan 512MB RAM 에서 Gemini base64 + Playwright 메모리 피크가 OOM 트리거 → 컨테이너 재시작 → dict 휘발. `GET /api/jobs/{id}` 가 영구적으로 404 반환하는데 frontend 폴링은 무한 반복.

**Phase J1 봉합 (구조 무변경 출혈만 차단)**:
1. **Frontend 폴링 retry-bound** (`lib/useJobPolling`) — 404 누적 ≥3 또는 5xx 누적 ≥3 시 `aborted=true` 로 즉시 중단 + ErrorBanner 안내. 단발 4xx (401/403 등) 는 카운터 누적 X — 일시적/영구적 구분
2. **ApiError 클래스** — fetchJson 이 status 를 throw 한다. retry-bound 카운터가 status 분기 가능하게
3. **재시작 알림** (`web/api/main.py` startup) — `notifier.send_text` 로 cold start 1회 push. RENDER_INSTANCE_ID 또는 hostname 식별, webhook 미설정 시 noop
4. **운영 env 동시성 하향** — `IMAGE_PARALLEL_WORKERS=2` / `BRIGHTDATA_CONCURRENT_LIMIT=3` / `BATCH_MAX_WORKERS=1` 로 메모리 피크 자체 축소

**Phase J2 구조적 해결 (보류, 운영 1주 후 결정)**: in-memory dict 를 캐시로 강등, Supabase `jobs` 테이블이 정본. 컨테이너 재시작 후 `status=orphaned` 로 자연 종결.

**일반화 규칙**:
- **in-memory state 가 정본인 endpoint** = 컨테이너 재시작 시 영구 404 함정. 재시작에 무방비한 코드는 `progress_log` jsonb 누적, `_jobs` dict, `republish_jobs` 만 in-memory 등 — Supabase write-through 또는 명시적 `orphaned` 종결 상태 필요
- **클라이언트 폴링은 항상 retry-bound 가져야 한다** — 무한 폴링은 백엔드 사고 시 트래픽 폭주 + 사용자 인지 차단의 이중 출혈. 카운터 + 영구 종결 (aborted) + 사용자 안내 동선 (결과 보관함 fallback) 셋이 묶여야 의미 있음
- **status 별 분기 카운터**: 일시적 (5xx) 와 영구적 (404) 을 같은 카운터로 누적하지 말 것. 200 OK 시 둘 다 reset, 영구 종결은 둘 중 하나만 임계 도달해도 발동
- **재시작 알림은 webhook noop 패턴** — `notifier.send_text` 가 webhook 없으면 즉시 return. dev 환경에서 수동 켜고 끌 수 있음. 토글 자체를 코드에 넣을 필요 X
- **plan 명은 dashboard ↔ render.yaml ↔ 마케팅 페이지 모두 다를 수 있음** — Render 의 경우 marketing 은 Standard 표기, dashboard 노출은 workspace tier 에 따라 다름. plan 변경 시 `render.yaml` enum 값 (`free`/`starter`/`standard`/`pro`/...) 과 dashboard 옵션을 양쪽 확인

**참조**:
- `web/frontend/src/lib/useJobPolling.ts` (retry-bound hook)
- `web/frontend/src/lib/api.ts:ApiError` (status 노출)
- `web/api/main.py:lifespan` (재시작 알림)
- `tasks/todo.md` Phase J1/J2 섹션

---

## vitest fake timer + waitFor 비호환 + Response 1회 read 함정 (2026-05-08)

**배경**: useJobPolling hook 회귀 테스트 작성 중 (`lib/__tests__/useJobPolling.test.tsx`) 첫 시도 5/5 fail.

**함정 1 — fake timer + `waitFor`**: `vi.useFakeTimers()` 사용 중 `@testing-library/react` 의 `waitFor` 는 내부 setTimeout polling 으로 조건을 기다리는데, fake timer 환경에서는 `setTimeout` 이 advance 안 되면 영원히 대기 → "Test timed out in 5000ms" 로 fail.

**해결**: `waitFor` 제거. `vi.advanceTimersByTimeAsync(ms)` 가 microtask 까지 처리하므로, 그 직후 `expect(result.current.X)` 직접 검증.

```ts
async function tick(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}
await tick(0);    // initial poll (microtask flush)
await tick(1000); // interval 1회
expect(result.current.aborted).toBe(true);
```

**함정 2 — Response 객체 1회 read 제한**: `mockResolvedValue(new Response(...))` 처럼 같은 Response 인스턴스를 반복 반환하면 두 번째 호출에서 `Body is unusable: Body has already been read` 에러. Web Streams 의 ReadableStream 은 1회 consume.

**해결**: `mockImplementation(() => Promise.resolve(new Response(...)))` 로 매 호출마다 새 Response 생성하는 factory 패턴.

```ts
function errorResponseFactory(status: number, text: string) {
  return () => Promise.resolve(new Response(text, { status }));
}
const fetchMock = vi.fn<typeof fetch>().mockImplementation(errorResponseFactory(404, "x"));
```

**시퀀스가 필요한 경우** — `mockResolvedValueOnce` 대신 index 카운터 + factory:

```ts
const sequence = [errorResponseFactory(404, "x"), jsonResponseFactory(running)];
let i = 0;
const fetchMock = vi.fn().mockImplementation(() => sequence[Math.min(i++, sequence.length - 1)]());
```

**일반화 규칙**:
- **`vi.useFakeTimers()` + `waitFor` 금지** — `advanceTimersByTimeAsync` 후 직접 `expect`. 두 API 는 같은 setTimeout queue 에서 동작이 충돌
- **`mockResolvedValue` 는 같은 객체 반복 반환** — Response/Stream/AbortController 등 1회용 객체는 `mockImplementation(factory)` 로 매번 새로 생성
- **fetch mock 의 시퀀스 전환** — `mockResolvedValueOnce` 체이닝 대신 factory + 카운터 패턴이 디버깅 쉽고 Response read 함정도 같이 해결
- **act + advanceTimersByTimeAsync 한 묶음**: helper `tick(ms)` 로 빼두면 테스트 가독성 ↑

**참조**:
- `web/frontend/src/lib/__tests__/useJobPolling.test.tsx` (5/5 통과 버전)
- `web/frontend/src/lib/useJobPolling.ts` (테스트 대상)

---

## Outline 실패 다층 진단 — silent except + max_tokens × OOM + 영속화 비활성 (2026-05-10)

**사고**: 사용자가 "원고 생성이 7단계에서 멈추고 HTML not found" 보고. 콘솔 에러는 모두 무관한 노이즈 (확장 프로그램 + iframe sandbox + 결과 404). 실제 [6] outline_generation 자체가 실패하고 있었고, 그것도 한 가지 원인이 아닌 **4개 layer 가 누적된 결합 사고**.

### 진단 단계별 발견

**Layer 1 — Silent except 가 traceback 차단**:
- `application/orchestrator._run_generation_stages` 의 4개 except 분기가 `stages.append(error=str(exc))` 만 하고 `logger.exception()` 호출 누락
- Render 로그에 traceback 안 찍힘 → 어느 단계에서 어떤 예외인지 불가시
- 사용자에게 응답 JSON 받아서 `result.stages[].error` 확인하고서야 첫 진단: `"outline tool_use 응답에 필수 필드 누락: ['keyword_plan']"`

**Layer 2 — max_tokens 잘림**:
- thinking off 분기 `max_tokens=4096` 으로 outline LLM 응답이 후반부에서 잘림
- title + intro + sections + image_prompts(5-8개) + keyword_plan + suggested_tags 합치면 평균 3500-4500 token → 4096 직격
- 응답 마지막 필드 (`keyword_plan`, `image_prompts`) 가 잘려 누락 → `_assert_required_fields` 가 `ValueError`
- 매 실행마다 누락 필드가 바뀌는 게 결정적 단서 (retry 로직이 못 고치는 종류 = 응답 자체 잘림)

**Layer 3 — Render Starter 512MB OOM**:
- max_tokens 16384 로 올리면 잘림 해결되지만, **메모리 spike** 가 OOM trigger
- Render Events 명시적 메시지: `Ran out of memory (used over 512MB)`
- 분석 [1]~[5] 누적 메모리 (16개 LLM 응답 객체 + scraped HTML + Pydantic 객체) + outline LLM 응답 16384 token spike (Anthropic SDK httpx response buffer + Pydantic transient) = 512MB 초과
- 인스턴스가 outline 응답 받자마자 죽고 자동 재시작

**Layer 4 — Job 영속화 default 비활성**:
- Phase J2 PR1~PR5 가 `jobs` 테이블 + write-through + heartbeat + GET fallback + sweep 인프라 다 구현
- 그러나 `JOB_PERSISTENCE_ENABLED` env default `false` → 운영상 비활성
- OOM 재시작마다 in-memory `JobManager._jobs` 휘발 → frontend retry-bound 가 aborted 상태로 종결 → 사용자가 본 "진행 상태를 더 이상 추적할 수 없습니다"

**부수 발견 — frontend ↔ backend type drift**:
- commit `09e9fec` (Phase J2 PR3) 가 `web/frontend/src/app/jobs/[id]/page.tsx:44` 에 `if (job?.status === "orphaned")` 분기 도입
- 그러나 같은 PR 의 `types/index.ts` 의 `JobStatus` union 에 `"orphaned"` 추가 누락
- Vercel build 가 TS2367 로 실패 → backend fix push 가 deploy 안 됨

### Layer 별 fix

| Commit | 변경 | 해결한 layer |
|---|---|---|
| `cbe1051` | outline retry + 4개 except 에 `logger.exception` | L1 — silent failure 종식 |
| `a4dfef6` | max_tokens 4096 → 8192 + truncation 감지 | L2 일부 (input 56k 키워드 통과) |
| `e81a4ee` | max_tokens 8192 → 16384 + `image_prompts` graceful 폴백 | L2 완전 (응답 잘림 해결, OPTIONAL_OUTLINE_FIELDS 도입) **→ 그러나 L3 OOM trigger** |
| `1586fee` | `JobStatus` union 에 `"orphaned"` 추가 | frontend type drift |
| `c4ee88a` | max_tokens 16384 → 8192 (롤백) + `gc.collect()` 분석/생성 사이 | L3 mitigation |
| (인프라) | Render Starter 512MB → Standard 2GB + `JOB_PERSISTENCE_ENABLED=true` | L3 근본 + L4 |

### 일반화 규칙

- **모든 except 분기에 `logger.exception` 필수** — `stages.append(error=str(exc))` 처럼 데이터로만 보존하면 traceback 손실. 운영 환경에서 traceback 없는 진단은 사용자 응답 JSON 수령 → 코드 추적 → 가설 수립 의 사이클이 길어진다. 비용 0 의 1줄 추가가 모든 후속 디버깅을 단축
- **LLM tool_use required field 누락 패턴**: 매 실행마다 다른 필드가 누락되면 retry 로직 무용 = 응답 자체 잘림. 첫 의심은 `max_tokens`. 같은 필드가 반복 누락되면 prompt/schema 문제
- **LLM 응답 max_tokens 와 인스턴스 메모리 한계 trade-off**: max_tokens 를 올리면 응답 spike 메모리 ↑. Anthropic SDK httpx response buffer + Pydantic parsing transient 가 합쳐져 인스턴스 메모리 한계 직격 가능. 단순 "올리면 해결" 이 아니라 plan capacity 와 함께 봐야 함
- **OPTIONAL_FIELDS graceful 폴백 패턴**: tool_use 의 일부 필드가 누락 가능성 있고 누락돼도 콘텐츠 발행이 가능하다면 (예: image_prompts → [9] 옵션 단계), `_REQUIRED_FIELDS` 에서 분리해 `_OPTIONAL_FIELDS` + Pydantic `default_factory` 로 graceful. raise 대신 logger.warning 으로 로그
- **Render Starter 512MB 는 LLM pipeline 에 부적합**: Python + FastAPI baseline ~100MB + Anthropic SDK ~30MB + 분석 누적 ~50-100MB + 본문 4섹션 병렬 응답 ~80MB + Gemini 이미지 ~80-200MB = 420-540MB. 마진 거의 없음. Standard 2GB 가 운영 최소
- **Job 영속화는 운영 환경에서 default `true` 필수**: Render OOM/restart, Vercel deploy 등 PaaS 의 인스턴스 lifecycle 이 분 단위로 발생. in-memory state 정본은 사고 시 추적 끊김 + 사용자 인지 차단. `JOB_PERSISTENCE_ENABLED=true` + Supabase `jobs` schema 적용 + write-through + GET fallback 4 종 세트가 묶여야 의미 있음
- **Frontend ↔ Backend status enum 동기화**: 새 status 값을 backend 에 추가할 때 (예: `"orphaned"`), frontend `types/index.ts` 의 union 도 같은 PR 에서 갱신. drift 가 다음 build 에서 TS2367 로 노출 — 단독 PR/배포 불가능
- **사용자가 본 콘솔 에러 ≠ 진짜 원인**: 브라우저 확장 프로그램 노이즈, iframe sandbox 경고, 결과 404 등은 모두 *증상 표시*. 진짜 원인은 백엔드 로그/응답 JSON 에 있음. 콘솔만 보고 진단 시도 금지, 즉시 응답 JSON 또는 백엔드 로그 요청
- **다층 사고는 한 번에 안 풀린다**: "outline 7단계에서 멈춤" 한 줄 증상이 4개 root cause (L1 silent except, L2 max_tokens, L3 OOM, L4 영속화) + 1개 부수 (frontend type drift) 의 결합. 한 fix 가 통과 못 하는 게 정상 — 통과 못 한 결과(다른 에러/같은 에러 다른 형태)가 다음 layer 의 단서

**참조**:
- `application/orchestrator.py:333-441` (4개 except + logger.exception)
- `domain/generation/outline_writer.py:_invoke` (max_tokens trade-off + retry 패턴)
- `domain/generation/outline_writer.py:_OPTIONAL_OUTLINE_FIELDS` (graceful 폴백)
- `web/frontend/src/types/index.ts:JobStatus` ("orphaned" 추가)
- Render Events 메시지: `Ran out of memory (used over 512MB)` (2026-05-10 14:23 PM)

---

## Chrome 136+ App-Bound Encryption v20 — CDP 자동 로그인 봉쇄 (2026-05-10)

`scripts/check_naver_login.py` PoC 검증 중 Profile 4 로 NID_AUT/NID_SES 추출이 어떤 경로로도 안 되는 것을 4단계 디버깅으로 확정. Chrome 127+ (운영 환경 136) 의 App-Bound Encryption v20 + CDP 보안 정책이 봉쇄선이다.

### [PUB-1] 임시 사본 user-data-dir → ABE v20 으로 NID_AUT 복호화 실패

`domain/publishing/auth.py:naver_login_cdp` 가 차용한 패턴은 `tempfile.mkdtemp()` → `shutil.copytree(Profile 4, tmp/Default)` → `--user-data-dir=tmp` + `--profile-directory=Default` + `--headless=new`. 정상 시작은 되지만 컨텍스트가 받는 쿠키에 NID_AUT/NID_SES 가 없다 — `BA_DEVICE, BUC, NAC, NACT, NM_srt_chzzk, NNB, PM_CK_loc, SRT30, SRT5` 만.

원본 DB 직접 검사 (`scripts/_inspect_cookies.py` SQLite 조회) 로는 NID_AUT 18행 중 정상 존재 확인. 즉 임시 디렉터리에서 Chrome 이 **새 encryption key 를 생성** → 원본 키로 암호화된 `encrypted_value` 복호화 실패. `Local State` 동반 복사 (`shutil.copy2(Path(user_data) / "Local State", tmp_user_data / "Local State")`) 로도 v10 키만 복원될 뿐 v20 키는 살리지 못한다 — v20 은 elevation_service COM API + 실행 파일 경로 바인딩이라 디렉터리 복사로 옮길 수 없다.

### [PUB-2] 원본 user-data-dir 직접 사용 → Chrome 이 CDP 활성화 거부

위 결론 후 코드를 "원본 User Data + `--profile-directory=Profile 4`" 직접 사용으로 변경 (`NAVER_CDP_USE_TMP_COPY=1` 환경변수로 옛 동작 토글). Chrome 은 떴는데 CDP 포트 9223 이 listen 안 됨 (`ECONNREFUSED 127.0.0.1:9223`). stderr 캡쳐 시 명확한 메시지:

```
DevTools remote debugging requires a non-default data directory.
Specify this using --user-data-dir.
```

Chrome 136 의 **보안 강화** 로 default User Data 경로를 `--user-data-dir` 로 명시하면 CDP 활성화 자체를 거부한다. 즉 임시 사본도 봉쇄(ABE), 원본도 봉쇄(CDP 정책) — **양쪽 모두 막혀** CDP 자동화 path 자체가 닫혔다.

### [PUB-3] browser_cookie3 직접 복호화 → 동일하게 실패

ABE v20 우회 후보로 `browser-cookie3==0.20.1` 시도. `browser_cookie3.chrome(domain_name='naver.com')` → `MAC check failed` + `BrowserCookieError: Unable to get key for cookie decryption`. 라이브러리도 v20 키를 풀지 못한다 (커뮤니티 issue 다수). pycookiecheat 등 다른 라이브러리도 동일 한계. **로컬 머신 권한으로도 v20 키는 elevation_service 통한 정식 호출만 가능**.

### [PUB-4] PoC 우회 — 수동 NID_AUT/NID_SES 주입

자동 추출이 모두 막힌 상황에서 PoC 검증 진행을 위해 `scripts/inject_naver_cookies.py` 추가. 사용자가 Chrome dev tools (F12 → Application → Cookies → www.naver.com) 에서 NID_AUT/NID_SES 값을 직접 복사 → getpass 로 stdin 입력 → `SessionManager.session.cookies.set(...)` → `.sessions/<name>.pkl` 저장. SessionManager 의 `_NAVER_DOMAINS = (".naver.com", "blog.naver.com", "cafe.naver.com")` 로 인해 load 시 도메인별로 펼쳐져 6개로 보인다.

이 PoC 로 dry-run 까지는 100% 검증 가능 — documentModel 69 components / SE 2.8.0 / 모든 노드 SE-uuid 정합 / `_publish_dryrun.json` 본체 보존 / `publishing_attempts` insert 모두 통과.

### [PUB-5] dry-run 저장은 `response_excerpt` 500자만 — orchestrator 보강 필요

`PublishResult.response_excerpt = json.dumps(document_model)[:500]` 발췌만 보존하므로 SE 변환 정합성을 dry-run 만으로 따질 수 없었다. `application/publishing_orchestrator.publish_from_output_dir` 의 dry-run 분기에서 `build_document_model` + `build_population_params` 를 한 번 더 호출해 `_publish_dryrun.json` 에 `document_model` / `population_params` 본체를 포함하도록 보강 (성능 영향 무시할 수준).

### [PUB-6] publishing_attempts 마이그레이션 누락 — best-effort 가 가시성을 가린다

`config/schema.sql:670` 에 정의된 `publishing_attempts` 테이블이 Supabase 에 적용되지 않은 상태. `_save_attempt` 가 try/except 로 감싸여 있어 본 흐름은 통과하지만 발행 시도가 영속되지 않아 사후 분석 불가. **best-effort 영속은 운영 가시성을 가리는 부작용** — schema migration 적용 여부를 PoC 시작 전 점검 단계 (e.g. `application` 테스트 fixture 또는 `scripts/check_db_migrations.py`) 에 포함시키는 게 안전.

### [PUB-7] 실 발행 차단점 — `errorCode="invalid parameter"` (모호한 응답)

NID_AUT + NID_SES + NNB 3개 쿠키 주입 후 실 발행 시도 시 RabbitWrite POST 도달 (200) + 응답 본문 `{"isSuccess":false, "result":{"errorCode":"invalid parameter", "errorMessage":""}}`. 어느 필드가 거부됐는지 서버가 명시 안 함.

운영 환경에서 정상 발행 1회 캡쳐 (Chrome Network → RabbitWrite Form Data) → 우리 dry-run 과 diff 결과 다음 차이 4가지를 식별·패치했지만 **여전히 거부**:

| 필드 | 차용본 default | 운영 캡쳐 값 | 패치 |
|---|---|---|---|
| `document.version` | `2.8.0` | `2.10.2` | document_builder.py |
| `populationMeta.directorySeq` | `21` (작성자 블로그 카테고리) | `0` | document_builder.py |
| `populationMeta.continueSaved` | `True` (임시저장 이어쓰기 모드) | `False` | document_builder.py |
| `populationMeta.autoByCategoryYn` | `True` | `False` | document_builder.py |

추가로 `_styled_node` 가 default plain textNode 에도 풀 nodeStyle 을 박는 것을 발견 (real 은 `style` 키 자체 부재). default 시 style 키 생략하도록 패치. 그래도 거부.

**최소 페이로드 (제목·본문 각 1글자) 시도** 결과 동일 거부 → components 콘텐츠 무관, 다른 필드가 직접 차단. `editorSource` 를 real 캡쳐값 (`tkx1thZgnyGrX4ObM3OQYA==`) 으로 바꿔도 거부 → **매 요청 새 토큰 발급**.

`SessionManager.get('https://blog.naver.com/<blog_id>/postwrite')` 응답 (200, 22KB SPA shell) 에 `editorSource` 또는 base64 16자 토큰 문자열 부재. SPA 가 후속 XHR 로 토큰을 받거나 클라이언트 JS 가 동적 생성. 다음 세션 진단: HAR 전체 캡쳐 (페이지 로드 ~ 발행 완료) → `editorSource` 발급 경로 식별.

**남은 차단점**: editorSource 동적 발급 경로. 이걸 풀어야 실 발행 1차 검증 가능. 이외 후보 (재현 시 다음 검증):
- `document.id` 포맷 — uuid hex (ours) vs Crockford base32 ULID (real). 양쪽 모두 26자
- `di.dio.dia` 의 `st`/`sk` 메트릭 (94/40 vs 186/6). 의미 미상

### 교훈

- **외부 보안 변경 (Chrome ABE v20, CDP 정책) 은 라이브러리·스크립트 차원에서 사전 차단된다** — 차용 출처 (`auto-publishing@c64b5e7`) 의 CDP 패턴은 c64b5e7 시점 기준으로 동작했지만 그 후 Chrome 의 보안 강화 2건 (`v20 ABE`, `default user-data-dir CDP 거부`) 으로 동시 봉쇄. 차용 시점 이후 Chrome 메이저 버전 차이는 publishing 류 코드의 회귀 위험 1순위
- **`errorCode` 가 모호한 외부 API 는 직접 비교만이 결정적** — 우리 측 가설로 1필드씩 바꿔보는 건 abuse 분류 위험. 운영 환경의 정상 트래픽 캡쳐 1회 → diff 가 가장 안전하고 빠르다
- **best-effort 영속은 가시성을 가린다** — 마이그레이션 누락이 사일런트하게 흡수되어 PGRST205 경고가 처음에 보였을 때만 발견. PoC 시작 전 migration 적용 점검을 자동화 필요
- **dry-run 저장은 검증 가능한 수준으로** — 500자 발췌는 진단 가치 0. PoC 도메인은 본체 보존이 default

**관련 변경**:
- `domain/publishing/auth.py` — Local State 동반 복사 + `NAVER_CDP_USE_TMP_COPY` 환경변수 (default 원본 직접 사용 시도)
- `application/publishing_orchestrator.py:165-186` — dry-run 시 documentModel/populationParams 본체 저장
- `domain/publishing/document_builder.py` — version 2.8.0 → 2.10.2, populationMeta 4필드 (`directorySeq`, `continueSaved`, `autoByCategoryYn`, `editorSource` real 캡쳐값) 정렬, `_styled_node` 가 default plain 시 `style` 키 생략
- `scripts/inject_naver_cookies.py` (NEW) — getpass 기반 NID_AUT/NID_SES/NNB 수동 주입
- `scripts/_inspect_cookies.py` (NEW) — Profile 의 Cookies SQLite DB 직접 조회 진단
- `scripts/_debug_publish_minimal.py` (NEW) — 제목·본문 1글자 최소 페이로드 발행 시도 (components 무관 확인)

**참조**:
- `tasks/todo.md` 의 Phase AP — 자동 발행
- `domain/publishing/CLAUDE.md`
- 차용 출처: `seokcess-kk/auto-publishing@c64b5e7`
- Chrome 보안 변경 추적: `https://issues.chromium.org/issues/40945783` (Application-Bound Encryption)

---

## insane-search 하이브리드 본문 fetcher 통합 (2026-07-06)

Bright Data(Web Unlocker, 유료) 비용 절감을 위해 오픈소스 insane-search 의 `curl_cffi` fetch 엔진을 **본문 수집 경로에만** 부분 도입했다. IP 로테이션이 없는 insane 의 한계를 **폴백 있는 하이브리드**로 흡수한다. PR1(HtmlFetcher Protocol) → PR2(vendor 벤더링) → PR3(어댑터) → PR4(라우팅+거버넌스) → PR5(본 기록) 5단계. 착수 전 확정한 핵심 의사결정 5건:

### [INSANE-1] insane engine 은 자립 Python 패키지 — 벤더링으로 재사용 (executor/Playwright 제외)

**결정**: insane-search 는 배포 형태가 Claude Code 플러그인이지만 내부 `engine/` 은 **자립 Python 패키지**(내부 100% 상대 import, curl-only 경로 존재)라, 폴더째 `vendor/insane_search/` 로 반입해 라이브러리로 취급했다. 최소집합 = 10개 `.py` + `waf_profiles.yaml`. **`executor.py`·`templates/`(Playwright Phase 3) 는 제외**했고, 그래도 안전한 이유는 `fetch_chain` 이 executor 를 **지연 import** 하기 때문 — `enable_playwright=False` 규약이면 top-level import 로 끌려오지 않는다.

**사유**:
- 벤더 위치를 `vendor/`(repo 루트 신규 패키지)로 둔 것은 domain 순수성 서사 보존 — `architecture-check.sh` 는 `domain/` 만 스캔하므로 `from vendor.insane_search...` 는 검사 대상 밖. `domain/crawler/_vendor/` 대안은 "도메인 안에 외부코드" 로 순수성을 흐려 기각.
- 내부가 100% 상대 import 라 **폴더 rename 자유 + 내부 코드 무수정**으로 반입 가능. 서드파티 추가는 `curl_cffi`(필수) + `pyyaml`(waf_profiles 로드) 둘뿐(bs4 는 기존 보유).
- 대가(패키징 배선 3건): `pyproject [tool.setuptools.packages.find] include` 에 `"vendor*"` 추가(= domain 의 `from vendor...` pyright resolve 관건), `ruff extend-exclude` 에 `"vendor"`(외부코드 린트 면제 — `print()`/bare except 등 원본 스타일 허용), Dockerfile 의존성 레이어에 vendor placeholder 선배치 + `COPY vendor/` + Docker 내 import 스모크.

**일반화 규칙**:
- **외부 도구의 "배포 형태"(플러그인/CLI)와 "내부 코드의 자립성"은 별개** — 내부가 상대 import + 의존성이 얇으면 벤더링으로 재사용 가능. import 그래프를 실사해 지연 import 경계를 먼저 확인.
- **비활성 기능(Playwright)은 지연 import 경계에서 자연 격리** — top-level import 부재를 확인하면 파일 물리 삭제 없이 제외 가능.

### [INSANE-2] 실측 근거 — 본문만 대체, SERP 는 Bright Data 유지, 완전 대체는 폴백으로

**결정**: 본문 수집(`m.blog.naver.com`)만 insane 으로 1차 대체하고, SERP(`search.naver.com`)·keyword_difficulty·ranking 은 Bright Data 를 그대로 유지. insane 자체가 IP 로테이션이 없어 완전 대체는 불가 → **폴백 하이브리드**(insane 실패 시 Bright Data)로 흡수.

**실측 근거(확정)**:
- **본문**: insane 이 단일 IP 로 120건 무차단 100% 성공 + 파서 결과가 Bright Data 와 **필드 단위 100% 일치** → 무손실 대체 가능.
- **SERP**: insane 의 WAF 검증기가 네이버 SERP 를 **challenge 로 오판**(grid 9회 소진) + 단일 IP 의 SERP rate 미검증 → Bright Data 유지가 안전.
- **완전 대체 불가**: insane 은 IP 로테이션 부재라 고동시성·장시간에서 차단 위험 → 폴백이 필수.

**일반화 규칙**:
- **"라이브러리에 기능이 있다" ≠ "우리 대상에서 작동한다"** — 대상별(본문 vs SERP) 실측으로 채택 경계를 그어야 한다(2026-04-15 Bright Data SERP API 교훈과 동형).
- **IP 로테이션 없는 무료 fetcher 는 폴백 하이브리드로만 안전** — 단일 IP 실측이 통과해도 배치 동시성/장시간은 미검증. 유료 폴백을 붙여 리스크를 흡수하고 폴백률을 usage 분포로 모니터링.

### [INSANE-3] 성공 판정 = `FetchResult.ok` 단일 신호 (verdict 문자열 열거 금지 / not_found 도 폴백)

**결정**: 어댑터의 성공 판정은 vendor `FetchResult.ok: bool` **단일 신호**로만 한다. verdict 문자열(strong_ok/weak_ok/challenge/...) 을 열거해 성공/실패를 재구성하지 않는다. 유일한 예외로 `verdict == "suspect_ok"`(부분성공, ok=False)만 **content sanity(최소 길이 500 + 차단마커 부재) 통과 시** 채택하고, 그 외 모든 실패는 `InsaneFetchError`(BrightDataTransientError 하위) raise 로 폴백 유도. **not_found(404) 도 폴백**한다 — Bright Data 도 404 라 폴백이 유료 낭비이지만, verdict 별 특례 분기로 단순성을 해치지 않는다("낭비 감수 + 단순성" > "404 특례로 얻는 소액 절감"; 부분성공 verdict 오판 위험이 더 큼).

**사유**:
- verdict 열거는 vendor 내부 상태에 어댑터가 결합돼, vendor 가 verdict 명을 바꾸면 성공 판정이 조용히 깨진다. `ok` 는 vendor 가 보증하는 안정 계약.
- `ok=True` 라도 content 에 차단마커/과소길이가 있으면 raise(2차 방어) — WAF 우회 실패를 신뢰 content 로 넘기지 않기 위함.

**일반화 규칙**:
- **외부 판정은 그 라이브러리가 보증하는 단일 bool 계약을 쓴다** — 파생 문자열 열거는 결합·회귀 위험. sanity 는 어댑터가 별도로 2차 검증.
- **비용 최적화 특례(404 스킵)가 로직 분기를 늘리면 단순성을 택한다** — 절감액 < 오판/유지비용이면 낭비를 감수.

### [INSANE-4] FallbackFetcher 는 record_usage 미호출(이중집계 차단) + 세마포어 실배선(no-op 방지)

**결정 (2중)**:
1. **usage 이중집계 차단**: `FallbackFetcher` 는 폴백 발생 시 `record_usage` 를 **호출하지 않고 `logger.warning` 만** 남긴다. 성공 usage 는 primary(insane, cost=0) 또는 fallback(BrightDataClient) 이 **각자** 기록한다. 폴백률은 `provider=brightdata + stage=page_scraping` usage 분포로 추론. InsaneFetcher 는 **성공 시에만** `record_usage(provider="insane")`, 실패(폴백 유도) 시 미기록.
2. **동시성 실강제**: insane 동시성은 `insane_fetcher.py` module-level `threading.BoundedSemaphore(settings.insane_concurrent_limit)` 로 `fetch()` 진입 시 `with` acquire — `brightdata_client._concurrent_semaphore` 패턴 미러. 설정값만 두고 세마포어에 배선하지 않으면 배치(BATCH_MAX_WORKERS 2~3)가 단일 IP insane 을 무제한 동시 타격하는 **no-op** 함정.

**사유**:
- 어댑터마다 usage 를 기록하는데 FallbackFetcher 까지 기록하면 성공 1건이 2번 집계돼 비용 리포트가 왜곡. "usage 를 기록하는 주체는 실제 fetch 를 수행한 최하위 fetcher 하나뿐" 규약.
- 단일 IP 리소스는 강제 메커니즘 없이는 설정값이 문서상 숫자로만 남는다.

**일반화 규칙**:
- **합성(래퍼) 계층은 usage/부수효과를 기록하지 않는다** — 실제 IO 를 수행한 잎(leaf) fetcher 만 기록. 래퍼는 관측(logger)만.
- **동시성 상수는 반드시 세마포어/락에 배선해 실소비 확인** — 정의만 하면 no-op. 테스트로 acquire 경로 진입을 고정(`test_fetch_acquires_semaphore`).

### [INSANE-5] 라우팅은 본문 경로만 교체 — SERP/ranking/keyword_difficulty 무변경 + env 즉시 롤백

**결정**: 라우팅 교체는 본문 경로(`application/stage_runner._build_body_fetcher()` → `run_stage_page_scraping`)에 국한한다. `_build_body_fetcher()` 는 `crawler_body_fetcher == "insane"` 이면 `FallbackFetcher(InsaneFetcher, BrightDataClient)`, 아니면 `BrightDataClient` 를 반환. `run_stage_serp_collection`·`keyword_difficulty_orchestrator`·`ranking_orchestrator` 는 `BrightDataClient` 를 **그대로 유지**. 문제 발생 시 **`CRAWLER_BODY_FETCHER=brightdata` env 한 줄로 코드 변경 없이 즉시 롤백**. 폴백용 Bright Data 키는 여전히 필수라 `_preflight_required_keys` 는 무변경(주석만 보강).

**사유**:
- 격리된 최소 교체 지점(팩토리 1개)만 바꾸면 SERP 계열 회귀 위험 0 + 롤백이 env 토글로 즉시. `application/orchestrator.py` 단일 흐름 4함수 시그니처는 무변경.
- 거버넌스 문서(`domain/crawler/CLAUDE.md` §금지 "대체 크롤링 라이브러리 금지" + `SPEC-SEO-TEXT.md` §3[2] "본문=Web Unlocker")는 코드가 본문=insane 으로 **실제 동작하는 순간(PR4)과 동반 착지** — 코드가 자기 거버넌스를 위반하는 과도기를 만들지 않기 위해.

**일반화 규칙**:
- **동작 전환은 단일 팩토리 분기 + env 토글로** — 최소 교체 지점 + 즉시 롤백. 단일 흐름 시그니처는 건드리지 않는다(additive only).
- **거버넌스 문서는 코드 활성화 PR 과 동반 갱신** — 문서 갱신을 뒤 PR 로 미루면 코드가 문서를 위반하는 과도기가 생긴다.

**참조**:
- `domain/crawler/fetcher.py` (HtmlFetcher Protocol 4종), `domain/crawler/insane_fetcher.py`, `domain/crawler/fallback_fetcher.py`
- `application/stage_runner.py:_build_body_fetcher`, `application/usage_tracker.py`(provider="insane"→0), `config/settings.py`(crawler_body_fetcher/insane_concurrent_limit/insane_timeout_seconds)
- `vendor/insane_search/`(v0.9.1, MIT), `tests/test_crawler/test_insane_fetcher.py` / `test_fallback_fetcher.py` / `test_insane_smoke.py`(RUN_INSANE_SMOKE opt-in)
- `tasks/todo.md` "insane-search 하이브리드 fetcher 통합" 섹션(PR1~PR5)

---

## insane-search SERP 확장 — 통합검색/블로그탭/난이도 하이브리드 (2026-07-06)

본문 하이브리드([INSANE-1~5]) 착지 후, insane 채택 경계를 **SERP·난이도 SERP** 로 확장했다. [INSANE-2] 에서 "SERP 는 insane WAF 검증기가 challenge 로 오판(grid 9회 소진)" 이라 Bright Data 유지로 그었던 경계를, **`success_selectors=["#main_pack"]` 튜닝 실측**으로 다시 그었다. PR-S1(InsaneFetcher 생성자 파라미터화) → PR-S2(SERP/난이도 라우팅 팩토리 + 토글) 2단계. ranking(PR-S3)은 부하 실측 게이트 선행이라 보류. 핵심 의사결정 4건:

### [INSANE-6] `success_selectors=["#main_pack"]` 한 방으로 3종 SERP challenge 완전 우회 (실측)

**결정**: insane 의 WAF 검증기가 네이버 SERP 를 challenge 로 오판(verdict grid 9회 소진 후 challenge 확정)하던 문제를, vendor `fetch` 의 `success_selectors` 인자에 **`#main_pack` 단일 셀렉터**를 주입해 해결했다. selector 가 DOM 에 존재하면 검증기가 즉시 `strong_ok`(1회)로 조기 판정 → grid 소진·challenge 오판이 사라진다.

**실측 근거(확정)**:
- **`#main_pack` 은 3종 SERP 공통 안정 컨테이너** — 통합검색(`where=nexearch`)·블로그탭(`where=blog`)·난이도 SERP 모두 이 컨테이너를 **정확히 1개** 포함. 트랙별 selector 분기 불필요(단일 selector 로 3종 커버).
- **verdict 전환**: selector 미지정 시 challenge(grid 9회 소진) → `["#main_pack"]` 지정 시 strong_ok(1회). WAF 우회 자체가 아니라 **검증기의 성공 판정 신호를 명시**한 것.
- **무손실 검증**: insane 파서 결과가 Bright Data 와 **블로그 URL 6/6 일치**. 단일 IP **30건 무차단**(분석 트랙은 on-demand·소량이라 30건 실측이 대표성 충분).

**일반화 규칙**:
- **"challenge = 실제 차단" 이 아니라 "검증기가 성공 신호를 못 찾음" 일 수 있다** — WAF 검증기에 대상 페이지의 안정 컨테이너를 성공 셀렉터로 명시하면 오판이 사라진다. 우회 코드 추가 전에 검증 파라미터부터 확인.
- **여러 대상 유형의 공통 안정 컨테이너 1개를 찾으면 분기가 사라진다** — 3종 SERP × selector 분기 대신 `#main_pack` 단일값. DOM 실사로 공통 컨테이너를 먼저 탐색.

### [INSANE-7] 대조군 challenge 는 실제 차단이 아니다 — soft:captcha 오탐 + selector 부정합 → 무손실 폴백

**결정**: [INSANE-6] 채택 전 대조군(selector 미지정) challenge 가 진짜 차단인지 확인했다. **실제 차단이 아니었다** — HTTP status 200 정상 응답인데 검증기의 `soft:captcha` 휴리스틱이 정상 SERP 를 captcha 로 오탐한 것. 따라서 selector 튜닝으로 안전하게 우회 가능하다고 판정.

**안전망(무손실)**:
- selector 가 미래에 부정합(네이버 DOM 개편으로 `#main_pack` 소멸/개명)이 되면, 정상 HTML 이어도 검증기가 다시 challenge 로 떨어진다 → `InsaneFetchError` raise → `FallbackFetcher` 가 **Bright Data 로 자동 폴백**. 결과 손실 0(폴백이 정상 수집).
- 즉 selector 튜닝은 **비용 최적화(insane cost=0 경로 확대)일 뿐, 정확도의 단일 의존점이 아니다**. 부정합 = 유료 폴백으로 흡수.

**일반화 규칙**:
- **status 200 + verdict challenge = 검증기 오탐 의심** — 실제 차단(403/429/captcha 페이지)과 검증기 휴리스틱 오탐을 status·body 로 구분한 뒤 우회를 판단.
- **selector 의존 최적화는 반드시 폴백 뒤에 둔다** — DOM 개편으로 selector 가 깨져도 폴백이 무손실을 보장하면 selector 는 "비용 밸브" 이지 "정확도 단일 의존점" 이 아니다.

### [INSANE-8] InsaneFetcher 생성자 파라미터화 — 트랙별 튜닝 주입, default 는 본문 무변경

**결정**: 본문/SERP 를 한 어댑터로 공용하되, `device_class`/`success_selectors`/`enable_phase0`/`max_attempts` 를 **생성자 키워드 인자**로 뺐다. default 는 본문 하드코딩 값과 동일(`device_class="mobile"`, `success_selectors=None`, `enable_phase0=True`, `max_attempts=_VENDOR_MAX_ATTEMPTS`)이라 `InsaneFetcher()` 는 기존 본문 동작을 그대로 유지. SERP 는 `InsaneFetcher(device_class="desktop", success_selectors=["#main_pack"])` 로 튜닝 주입.

**파라미터화하지 않은 2개(의도적 고정)**:
- `enable_playwright=False`·`enable_learning=False` 는 **생성자 인자로 노출하지 않고 `_call_vendor` 에 하드코딩 유지**. 이유: curl-only 격리(Playwright 영구 금지)·홈디렉터리 파일쓰기 차단은 트랙 무관 불변 규약이라, 파라미터로 열면 실수로 True 주입되는 표면이 생긴다. "튜닝 가능한 축" 과 "불변 안전 규약" 을 생성자 시그니처에서 물리적으로 분리.

**일반화 규칙**:
- **공용 어댑터의 트랙별 차이는 생성자 인자로, 안전 불변 규약은 하드코딩으로** — 파라미터화 표면 = 잘못 주입될 표면. 불변값을 인자로 열지 않으면 오용 자체가 불가능.
- **default = 기존 동작** 로 두면 기존 호출부(`InsaneFetcher()`) 무변경 + 신규 호출부만 튜닝 주입. additive only 를 시그니처 레벨에서 보장.

### [INSANE-9] 라우팅은 분석 트랙 SERP 만 — ranking 은 부하 실측 게이트 선행(PR-S3 보류)

**결정**: `crawler_serp_fetcher` 토글(default `insane`)을 신설해 **`collect_serp`(분석 트랙 SERP) + `keyword_difficulty`(난이도 SERP)** 만 하이브리드로 라우팅. 팩토리는 `stage_runner._build_serp_fetcher()` 단일 출처이고, `keyword_difficulty_orchestrator._build_client()` 가 이를 **application↔application cross-import** 로 재사용(selector/토글 단일 출처 — application/CLAUDE.md 상 허용). **ranking 은 default `brightdata` 조차 도입하지 않고 Bright Data 단독 유지**.

**ranking 을 보류한 사유(게이트)**:
- ranking 은 **매일 cron 대량 측정**(publication N개 × 매일). 실측은 분석 트랙 기준 **단일 IP 30건까지만** 검증됨 → 100+ 동시성·장시간 무차단은 미검증.
- insane 은 IP 로테이션 부재([INSANE-2])라 대량 트래픽에서 차단 위험이 실재. 30건 실측을 100+ 로 확대 적용하는 것은 근거 없는 외삽.
- 따라서 PR-S3(ranking 확장)은 **100+ 부하 실측 게이트를 선행 조건으로** 보류. default brightdata 도입도 안 함(부하 실측 전에는 ranking 경로에 insane 을 아예 배선하지 않음).

**일반화 규칙**:
- **실측 표본의 대표성 밖으로 채택을 외삽하지 않는다** — on-demand 소량(30건) 실측은 분석 트랙엔 충분하나 대량 cron(100+)엔 부족. 트래픽 프로파일이 다르면 별도 게이트.
- **라우팅 토글은 트랙별로 분리해 부분 채택을 안전하게** — 본문 `crawler_body_fetcher` / SERP·난이도 `crawler_serp_fetcher` / ranking(미도입). 트랙별 토글이면 한 트랙 문제가 다른 트랙으로 번지지 않고 env 로 개별 롤백.

**참조**:
- `domain/crawler/insane_fetcher.py:InsaneFetcher.__init__`(생성자 파라미터화), `_call_vendor`(playwright/learning 하드코딩 고정)
- `application/stage_runner.py:_build_serp_fetcher` + `_SERP_SUCCESS_SELECTOR="#main_pack"`, `run_stage_serp_collection`(client 타입 `HtmlFetcher` 로 확장)
- `application/keyword_difficulty_orchestrator.py:_build_client`(stage_runner cross-import 재사용)
- `config/settings.py:crawler_serp_fetcher`(default insane), `config/.env.example`(CRAWLER_SERP_FETCHER)
- `tests/test_crawler/test_insane_fetcher.py`(생성자 파라미터화 3종), `tests/test_application/test_stage_runner.py:TestSerpFetcherRouting`, `tests/test_application/test_keyword_difficulty_orchestrator.py:TestBuildClientRouting`

## insane-search 어댑터 sanity 버그 + ranking 확장 (2026-07-06)

SERP 확장([INSANE-6~9]) 착지 후, ranking 부하 실측 진단 중 **어댑터 잠복 버그 1건**을 발견·수정하고, 그 실측을 근거로 [INSANE-9] 가 게이트로 보류했던 **ranking 트랙까지 insane 을 확장**했다. 핵심 의사결정 2건:

### [INSANE-10] 어댑터 content sanity 의 captcha false positive → strong_ok 우회

**발견**: ranking 부하 실측 진단에서 `adapter_content_sane=0/130` (어댑터 sanity 전량 실패). 원인 추적 결과 — 정상 네이버 SERP(통합검색/블로그탭/난이도)가 `captcha.nid.naver.com` config 스크립트를 **페이지당 8회씩 임베드**해 `"captcha"` 문자열이 항상 존재. 실제 차단 문구(`자동등록방지`)는 0건. `InsaneFetcher._content_is_sane` 의 `_BLOCK_MARKERS` 에 bare `"captcha"` 가 있어 정상 SERP 를 **100% reject** → `strong_ok`(`#main_pack` positive proof)여도 `InsaneFetchError` → **항상 Bright Data 폴백**(insane 이득 0).

**핵심 함정 — 무손실 폴백이 버그를 은폐**: 폴백이 Bright Data 로 정상 수집하므로 URL 일치·수집 건수는 모두 정상. **동작은 정상, 비용절감만 0** 이라 결과 검증으로는 버그가 표면에 안 드러난다. 실측 진단(어댑터 sanity 를 지표로 미러링)이 아니었으면 못 잡았을 잠복 버그.

**수정**: `_accept` 가 `verdict == "strong_ok"`(vendor Layer 5 가 우리 success_selector `#main_pack` 매칭을 확인한 강한 positive proof)이면 content sanity 재검을 **스킵**. `_content_is_sane`/`_BLOCK_MARKERS` 자체는 **유지** — 본문 경로는 selector 없는 `weak_ok` 휴리스틱이라 sanity 2차 방어가 여전히 필요하고, 본문 HTML 에는 captcha config 임베드가 없어 무영향.

**일반화 규칙**:
- **success_selector positive proof 는 우리 소프트마커 재검보다 강한 신호** — vendor 가 우리 지정 셀렉터 매칭을 확인했으면(strong_ok) 우리 쪽 문자열 휴리스틱(`"captcha"` 포함 여부)으로 2차 부정하지 말 것. 강한 positive proof 가 약한 heuristic 을 이긴다. 단, proof 가 약한(weak_ok) 경로에서는 소프트마커 2차 방어를 유지.
- **소프트 blocklist 마커는 대상 페이지의 정상 임베드와 충돌할 수 있다** — bare `"captcha"` 는 네이버가 정상 SERP 에 captcha config 를 임베드하는 순간 false positive. 마커는 실제 차단 문구(`자동등록방지`)처럼 대상 특이적으로 좁혀야 오탐이 없다.
- **무손실 폴백은 비용 버그를 은폐한다** — 폴백이 결과를 살리면 "동작 정상 / 비용만 0" 버그는 결과 검증으론 안 보인다. 비용 경로(어댑터 채택률 = adapter sanity)를 별도 실측 지표로 미러링해야 잡힌다.

### [INSANE-11] ranking cron SERP 단일 IP 대량 부하 — 130건 실측으로 게이트 통과

**배경**: [INSANE-9] 는 ranking(매일 cron 대량)을 "단일 IP 30건까지만 실측 → 100+ 미검증" 이라 보류(PR-S3)했다. 이번에 그 게이트를 **130건 순차 부하 실측**으로 통과시켰다.

**실측 설계·결과**:
- **A(세션 재사용)** / **B(매 요청 `POOL.reset()` = 실제 ranking 이 `client.close()` 하는 패턴)** 각 130건 순차, `sleep = ranking_check_sleep_seconds = 1s`.
- **양 시나리오 130/130 무차단 100% strong_ok**, `executed_attempts ≥ 2 = 0`(전부 1회 성공). 오늘 단일 IP 누적 ~410 요청에도 감쇠 0.
- A/B latency 거의 동일 → **매 요청 close 하는 실제 ranking 패턴도 안전**. 세션 재사용 최적화는 불필요(과잉).

**결정**: `ranking_serp_fetcher` 토글 신설, default **insane**. **분석 트랙 `crawler_serp_fetcher` 와 독립 토글** — cron 대량 경로를 분석과 별개로 즉시 롤백 가능. `build_serp_fetcher(fetcher_choice)` 파라미터화로 분석(`crawler_serp_fetcher`)/ranking(`ranking_serp_fetcher`)이 각자 토글을 참조(팩토리는 단일 출처 유지, 인자로 트랙 분기).

**한계·안전망**:
- **130건까지만 실측** — 그 이상 임계는 미측정. IP 로테이션 부재([INSANE-2])는 그대로라, 임계 초과 차단이 발생해도 `FallbackFetcher → Bright Data` 폴백이 유일하지만 무손실 안전망.
- 즉 채택은 "130건 실측 + 무손실 폴백" 위에 선다. 임계 초과 차단이 나도 결과 손실 0.

**일반화 규칙**:
- **부하 게이트는 실제 운영 패턴(매 요청 close)까지 재현해 통과** — 세션 재사용(A)만 통과시키면 실제 cron 이 다르게 동작(B)할 때 무효. B(매 요청 `POOL.reset()`)까지 동일 결과여야 게이트 통과로 인정.
- **트랙별 독립 토글로 부분 채택** — 같은 팩토리라도 `crawler_serp_fetcher`(분석) / `ranking_serp_fetcher`(cron)를 분리하면 한 트랙 차단이 다른 트랙으로 안 번지고 env 로 개별 롤백.
- **실측 범위를 명문화하고 그 밖은 폴백에 위임** — "130건까지 무차단, 그 이상 미검증" 을 명시. 외삽하지 않고 폴백을 안전망으로 선언하는 게 정직한 채택.

**참조**:
- `domain/crawler/insane_fetcher.py:_accept`(strong_ok 시 sanity 스킵), `_STRONG_OK_VERDICT`, `_content_is_sane`/`_BLOCK_MARKERS`(유지 — 본문 weak_ok 2차 방어)
- `application/stage_runner.py:build_serp_fetcher(fetcher_choice)`(파라미터화 public 팩토리)
- `application/ranking_orchestrator.py:440`(`build_serp_fetcher(settings.ranking_serp_fetcher)`), `application/keyword_difficulty_orchestrator.py:50`(`crawler_serp_fetcher` 재사용)
- `config/settings.py:ranking_serp_fetcher`(default insane, 독립 토글) / `crawler_serp_fetcher`, `ranking_check_sleep_seconds`

