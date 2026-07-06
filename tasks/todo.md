# Contents Creator — Todo

> 현재: Phase 0 부트스트랩 완료 → Phase 0.5 SEO 실측 완료 → **Phase 0.6 브랜드 카드 실측 블로킹**
>
> 두 트랙 병행: SEO (기존 Phase 1~7) + 브랜드 카드 (신규 Phase B1~B9). 합류 use case = `run_full_package`.

## ✅ 완료 인덱스 (상세: tasks/_archive/todo-2026-q2.md)

- 부트스트랩 + 초기 설계 (2026-04-15) — 14 항목
- Phase 1 SEO 크롤러 / Phase 2 실측 (P2-I1/I2) / Phase 2~8 SEO 트랙 (2026-04-15 ~ 04-29)
- Phase R1~R7 순위 추적 시스템 MVP (2026-04-29) — SPEC-RANKING.md
- Phase U0~U12 UI 압축 + 브랜드 카드 + 외부 검토 P0/P1 (2026-04-27 ~ 04-28) — commit 8774267 등
- Phase B7~B19 Batch Pipeline 후속 PR (2026-05-04 ~ 05-05) — SPEC-BATCH.md

---

## 🚀 Phase AP — 자동 발행 (Auto-Publishing)

> 2026-05-10 시작. `seokcess-kk/auto-publishing@c64b5e7` (MIT, MoonbirdThinker) 의 RabbitWrite + CDP/RSA 인증 자산을 차용.
> 결정사항: 풀 SE 변환 (목표) / LRU 5채널 / 검수 통과 자동 / **PoC 부터 (단일 블로그·평문)**.
> 운영 가드: `PUBLISHING_ENABLED` env, `--dry-run`, 발행 직전 의료법 재검증, 발행 시도 로그 영속.

### Phase AP-A — PoC: 단일 블로그 평문 발행 (집중)

새 도메인 `domain/publishing/` (격리). naver_publisher 가 RabbitWrite POST 한 번 성공시키는 것이 acceptance.

- [x] AP-A1 `domain/publishing/CLAUDE.md` — 도메인 규칙 + 차용 출처 명시
- [x] AP-A2 `domain/publishing/model.py` — `PublishRequest`, `PublishResult`, `PublishingError` Pydantic
- [x] AP-A3 `domain/publishing/session.py` — `SessionManager` (.sessions/<channel>.pkl) 차용
- [x] AP-A4 `domain/publishing/auth.py` — `naver_login_cdp` + `naver_login` (RSA 폴백) 차용. logger 우리 `logging.getLogger`
- [x] AP-A5 `domain/publishing/document_builder.py` — PoC: `seo-content.html` → SE paragraph 평문화 (`<h2>` → bold paragraph, `<p>` → paragraph). `<img>/<table>/<blockquote>` 는 [PLACEHOLDER] 텍스트
- [x] AP-A6 `domain/publishing/naver_publisher.py` — `NaverBlogPublisher.publish(req: PublishRequest) -> PublishResult`. RabbitWrite POST + logNo 추출
- [x] AP-A7 `application/publishing_orchestrator.py` — `publish_from_output_dir(output_dir, channel, keyword, *, dry_run=False)`: 콘텐츠 fetch → publisher 호출 → publishing_attempts 영속 → register_publication. **의료법 재검증은 Phase AP-B 로 이월** (PoC 신뢰 가정 + block_medical_auto_publish 안전망)
- [x] AP-A8 `scripts/publish.py --slug --channel-id [--ts] [--keyword] [--dry-run] [--no-register]` 얇은 CLI
- [x] AP-A9 `config/settings.py` 환경 변수: `publishing_enabled`, `naver_username/password`, `naver_chrome_profile`, `chrome_path`, `min_publish_interval_minutes`, `block_medical_auto_publish`. (.env.example 동기화)
- [x] AP-A10 발행 시도 로그 — `domain/publishing/storage.py` + `publishing_attempts` 테이블 schema (id/channel_id/slug/job_id/status/post_url/post_id/message/response_excerpt/attempted_at)
- [x] AP-A11 `--dry-run` 시 documentModel JSON 만 `output/{slug}/{ts}/_publish_dryrun.json` 저장
- [x] AP-A12 단위 테스트: `tests/test_publishing/test_document_builder.py` — 16 케이스 (SE 스펙·요소별 변환·placeholder·population_params 가드) ✅
- [ ] AP-A13 **사용자 작업 + 1회 실 발행 검증** — Supabase 에 `publishing_attempts` 테이블 마이그레이션 적용 → `.env` 에 `PUBLISHING_ENABLED=true` + `NAVER_CHROME_PROFILE=Profile X` 설정 → 등록된 1채널로 dry-run → 실 발행 → 네이버에서 노출 확인 → publication 자동 등록 확인

### Phase AP-B — 풀 SE 변환기 + 이미지 업로드 (Phase A 완료 후)

- [ ] AP-B1 SE 컴포넌트 변환 확장: `<table>`, `<blockquote>`, `<ul>/<ol>`, `<strong>`, `<em>`, headings (h2/h3 별 폰트)
- [ ] AP-B2 **네이버 이미지 업로드 API 리버스** (auto-publishing 미구현 부분, 가장 큰 unknown). 글쓰기 페이지 network trace → endpoint 식별 → multipart 업로드 → 응답 image URL 을 SE `image` 컴포넌트로 삽입
- [ ] AP-B3 카테고리 매핑: `category_no` 자동 조회 (블로그 카테고리 목록 fetch)
- [ ] AP-B4 변환 fixture 12개 snapshot 테스트 (DIA+ 풍부 케이스 포함)

### Phase AP-C — 5개 LRU 로테이션 + 검수 큐 자동 통합

- [ ] AP-C1 `blog_channels` 테이블에 `last_published_at TIMESTAMPTZ`, `chrome_profile TEXT NULL`, `naver_account_label TEXT NULL` 추가 (마이그레이션)
- [ ] AP-C2 `domain/publishing/channel_selector.py::pick_lru_channel()` — 가장 오래 발행 안된 채널 선택 + min_interval 가드
- [ ] AP-C3 `application/publishing_orchestrator.py::auto_publish_approved_items()` — 검수 큐 approve 시 자동 트리거
- [ ] AP-C4 `POST /batches/{id}/publish-now` API + `/queue` 페이지 액션 버튼
- [ ] AP-C5 의료 키워드 차단 옵션 — `BLOCK_MEDICAL_AUTO_PUBLISH=true` 시 의료 카테고리 자동 발행 거부 (수동만 허용)
- [ ] AP-C6 `docs/auto-publishing-setup.md` — 5채널 Chrome 프로필 운영 가이드 (Windows 로컬)

## ⏸ 사용자 샘플 대기 — Phase 0.6 잔여 (BC-3/BC-4)

> 2026-05-08 정밀 정리 — Phase 0.5 SEO 실측 + Phase 0.6 브랜드 카드 실측 완료 항목은 archive 이관.
> BC-3 PDF / BC-4 docx 만 사용자 샘플 대기. 상세는 `tasks/_archive/todo-2026-q2.md` 참조.

### [BC-3] PDF 파싱 실측 (pypdf → pdfplumber fallback) ⏸ 사용자 샘플 대기
- [x] 의존성 설치 완료: pypdf 6.10.2, pdfplumber 0.11.9
- [ ] 사용자 준비: 한글 PDF 3종 (스캔·텍스트·혼합)
- [ ] pypdf 로 각 PDF 의 텍스트 추출 시도
- [ ] 빈 텍스트/깨짐 시 pdfplumber 로 fallback
- [ ] 스캔 PDF fallback 정책 결정
- [ ] 결과·정책을 `tasks/lessons.md` BC-3 섹션에 기록

### [BC-4] docx 파싱 실측 (python-docx) ⏸ 사용자 샘플 대기
- [x] 의존성 설치 완료: python-docx 1.2.0
- [ ] 사용자 준비: 표 포함 docx 1개
- [ ] paragraph + 표 셀 flatten
- [ ] 텍스트 순서·표 내용 정확 추출 확인
- [ ] 결과를 `tasks/lessons.md` BC-4 섹션에 기록


---

## 🎨 Phase B1~B9 브랜드 카드 잔여 — 운영 안정 후 검토

> 2026-05-08 정밀 정리 — 메인 구현 완료, archive 이관. 후속 잔여만 보존.

- [ ] **잔여**: `block_rules.py` 별도 파일로 분리되지 않음 — `model.py` 안의 `BlockId` Enum 외에 `BLOCK_MEDIA_MAPPING` 상수 명시적 정의 부재. 향후 §3-2-1 정합 검증 시 추가 검토
- [ ] **잔여**: `prompt_builder.py` 단일 진입점 미구현 — LLM 프롬프트가 `plan_generator.py` + `compliance.py` 에 분산. 단일 진입점 통합 필요 여부는 운영 안정 후 재검토
- [ ] **잔여**: `application/stage_runner.py` 의 `run_stage_brand_source_loading`/`run_stage_brand_asset_extraction` 미구현 — `application/brand_card_orchestrator.py` 가 도메인을 직접 호출. Phase B9 통합 시 일괄 정리
- [ ] **잔여**: `card_plan_validator.validate_card_plan()` 별도 함수 미구현 — Pydantic `model_validator` 로 분산 검증. 명시적 [B4] 재호출 피드백 생성 로직 추가 검토 필요
- [ ] **잔여**: `application/stage_runner.run_stage_card_planning` 미구현 — Phase B9 통합 시 일괄 정리
- [ ] **잔여**: `application/stage_runner.run_stage_image_slot_generation` 미구현 — `brand_card_orchestrator._prefetch_ai_images` 가 인라인 처리. Phase B9 통합 시 정리
- [ ] **잔여**: 5번째 템플릿 미구현 — SPEC §B5 는 5종 명시. 운영 키워드 다양성 확인 후 추가 여부 결정
- [ ] **잔여**: `application/stage_runner.run_stage_card_html_render` 미구현 — Phase B9 통합 시 정리
- [ ] **잔여**: `application/stage_runner.run_stage_card_compliance` 미구현 — Phase B9 통합 시 정리
- [ ] **잔여**: 실 키워드 + 실 브랜드로 `run_full_package` 끝까지 통과시키는 통합 E2E 테스트 — Bright Data/Anthropic/Gemini/Supabase 실호출 필요. 운영 진입 시점에 별도 진행
- [ ] **P1 잔여 (B9 와 통합)**: `application/stage_runner.run_stage_card_screenshot` — Phase B9 의 stage_runner 통합 작업에 흡수

### 선택 항목 (운영 안정 후 검토)
- [ ] **선택**: `.claude/skills/brand-card/` 스킬 + `.claude/agents/domain/brand-card-guardian.md` 에이전트 — 도메인 일관성 가디언, 운영 안정 후 추가 검토

---

## 🔍 Phase K6/K7 잔여 — 사용자 작업 + 수동 검증

> 2026-05-08 정밀 정리 — K1~K5 + K7 코드 완료 archive 이관. 검증·사용자 작업만 보존.

### Phase K6 — 검증 + 커밋
- [ ] K6.2 수동 smoke (Supabase 스키마 적용 후) — 단일 분석 + 10개 대량 → /keywords 페이지에서 등급 표시 확인
- [ ] K6.3 commit + push

### Phase K7 — 네이버 검색광고 API 통합 (사용자 작업 2건)
- [ ] K7.5.b **사용자 작업**: Supabase SQL Editor 에서 ALTER TABLE 실행 (또는 schema.sql 13번 섹션 재실행 — IF NOT EXISTS 라 안전)
- [ ] K7.11 **사용자 작업**: Render 환경 변수 추가 — `NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`, `NAVER_AD_CUSTOMER_ID`

---

## ⚡ Phase F5 — 모바일 SERP 전환 (PoC 대기)

> 2026-05-08 정밀 정리 — F1~F4 완료 archive 이관. F5 PoC 만 잔존.

### Phase F5 — 모바일 SERP 전환 (파서 재작성 — 신중) ⏸ PoC 대기
- [ ] F5.1 `m.search.naver.com` SERP HTML fetch + 구조 분석 (PoC fixture 8개)
- [ ] F5.2 PC SERP 와 동일 등급 판정 일치도 검증 (5/8 이상이면 채택 검토)
- [ ] F5.3 파서 분기 또는 신규 모듈 작성
- [ ] F5.4 fetch 시간 비교 — 1~2초 단축 시 채택, 정확도 손실 시 보류

> 결과 (F1~F4 적용 후 추정):
> - 단일 분석: 6~12초 → **5~10초** (검색량 병렬화 + 캐시 hit 시 1초 미만)
> - 배치 50개: 200초 → **약 50초** (parallel 8 + sleep 0.3, 4배 ↑)
> - 사용자 체감: 진행률 바 + 부분 결과 즉시 표시로 "기다림" 인식 약화

---

## ☁️ Phase D2~D5 — 클라우드 배포 잔여 (사용자 작업)

> 2026-05-08 정밀 정리 — D1 백엔드 컨테이너 archive 이관. D2~D5 사용자 작업만 잔존.

### Phase D2 — 사용자 작업: Supabase Storage 버킷
- [ ] D2.1 Supabase 대시보드 → Storage → New Bucket → name: `results`, **Private**
- [ ] D2.2 RLS 정책: service_role 키로 업로드 + signed URL 만 외부 노출 (Supabase 기본값으로 충분)

### Phase D3 — 사용자 작업: Render 백엔드 배포
- [ ] D3.1 Render 대시보드 → New Web Service → GitHub 연결 → contents-creator repo
- [ ] D3.2 자동 감지된 `render.yaml` 적용 → `contents-creator-api` 서비스 생성
- [ ] D3.3 환경 변수 8개 입력 (Render 대시보드의 Environment 탭):
  - `ANTHROPIC_API_KEY`
  - `GEMINI_API_KEY`
  - `BRIGHT_DATA_API_KEY`
  - `BRIGHT_DATA_WEB_UNLOCKER_ZONE`
  - `SUPABASE_URL`
  - `SUPABASE_KEY` (service_role 권장 — Storage 업로드용)
  - `CORS_ORIGINS` = `https://contents-creator.vercel.app` (Vercel 도메인 확정 후)
  - `ADMIN_API_KEY` = 임의 32자 랜덤 (예: `openssl rand -hex 32`). Vercel `NEXT_PUBLIC_API_KEY` 와 동일값
- [ ] D3.4 첫 배포 — 빌드 5~8분 (Playwright Chromium 다운로드 포함)
- [ ] D3.5 `https://contents-creator-api.onrender.com/health` 200 확인
- [ ] D3.6 `/docs` (Swagger) 접속해 모든 엔드포인트 표시 확인

### Phase D4 — 사용자 작업: Vercel 프론트엔드 배포
- [ ] D4.1 Vercel 대시보드 → New Project → GitHub contents-creator repo → Root Directory `web/frontend`
- [ ] D4.2 환경 변수 입력:
  - `BACKEND_API_URL` = `https://contents-creator-api.onrender.com` (서버사이드 rewrites 용)
  - `NEXT_PUBLIC_WS_URL` = `wss://contents-creator-api.onrender.com` (WebSocket)
  - `NEXT_PUBLIC_API_KEY` = D3.3 의 `ADMIN_API_KEY` 와 동일
- [ ] D4.3 자동 빌드 → `https://contents-creator.vercel.app` (또는 자동 부여 도메인)
- [ ] D4.4 Vercel 도메인 확정 후 Render 의 `CORS_ORIGINS` 갱신 (D3.3 재방문)

### Phase D5 — 운영 확인
- [ ] D5.1 `/keywords` 페이지 접속 → 단일 키워드 분석 → 등급 표시 확인
- [ ] D5.2 `/rankings` 페이지 접속 → 기존 publication 목록 확인
- [ ] D5.3 SEO 파이프라인 1건 실행 → output → Supabase Storage 업로드 + Signed URL 조회 확인
- [ ] D5.4 Render Metrics 탭에서 Memory 사용량 모니터링 (480MB+ 상시면 Standard 업그레이드)
- [ ] D5.5 비용 모니터링 알림 — Anthropic/Bright Data/Gemini 대시보드에서 일·월 한도 설정

---


---

## 📦 P2 이후 — long-form 확장 트랙 (보류)

> SPEC §2 "P1 제외" 항목. 인스타 표준 1080×1350/1920 카드를 넘어서는 상세페이지형 long-form PNG 가 필요한 시점에 진입.
> 2026-04-29 신설 — Phase B7 에서 이관.

- [ ] **9000px 초과 자동 분할 알고리즘** — `page.evaluate()` 로 블록 y좌표 추출 → 그리디 분할 → Pillow 크롭. 마지막 조각 4000px 미만 예외 허용 (lessons BC-7 §2-4 보완)
- [ ] **PNG `tEXt` 메타 삽입** — 브랜드 ID, 키워드, 템플릿 ID, variant 를 PIL `PngImagePlugin.PngInfo` 로 임베딩
- [ ] **hard max 18000px 초과 시 variant 실패 분류** — `RenderError("max_height_exceeded")` → variant skip
- [ ] long-form 전용 템플릿 (`clinic-classic` 등 SPEC v1 명명 활용 가능)

---

## ⚠️ 사용자 제공 대기 중

- ~~**의료법 8개 카테고리 상세 (`SEO_STRICT`)**~~ — Phase 5 완료로 해소 (10 카테고리 확정, 2026-04-29)
- **Phase 0.6 실측 샘플** — PDF 3종 (스캔/텍스트/혼합), docx 1종 (표 포함). BC-3/BC-4 가 이를 대기 중
- **BC-5 실존 한의원 홈페이지 5~10곳 URL** — 로고 자동 추출 성공률 집계용
- **P2-I1 블로그 태그 수집 정책 결정** — (a) PostView.nhn iframe 실측 / (b) 별도 JSON API 탐색 / (c) SPEC 에서 전면 삭제 중 택일
- ~~**MVP 템플릿 5종**~~ — 4종 구현 완료. 5번째 추가 여부는 운영 키워드 다양성 확인 후 결정

## 📌 상시 확인

- [ ] 코드 변경 시 `bash .claude/hooks/build-check.sh` 통과
- [ ] 의료 콘텐츠 관련 변경 시 `python scripts/validate.py` 추가 실행
- [ ] 브랜드 카드 관련 변경 시 `domain/brand_card/` import 규칙 확인 (다른 도메인 import 금지, compliance/rules.py 만 예외)
- [ ] 사용자 교정 받으면 즉시 `tasks/lessons.md` 에 기록

---

# 순위 추적 시스템 (Ranking Tracker) MVP — 2026-04-24 착수

> 목표: 발행한 SEO 원고의 네이버 통합검색 순위를 매일 자동 측정해 피드백 루프 완성.
> SPEC 참조: SPEC-SEO-TEXT.md §3 [1] (SERP 수집 — 재사용), §12 (application 레이어 규칙)
> CLAUDE 규칙 준수: 레이어 import 단방향, Pydantic 반환, settings 단일 출처, Bright Data 단일 클라이언트, 30줄/300줄 한계
>
> 사용자 결정 (불변):
> 1. URL 입력 = 사용자 직접 등록 (도메인 매칭은 Phase 2 별건)
> 2. 한 PR 에 backend+API+UI+CLI+tests 일괄
> 3. 매일 1회 누적
> 4. 기존 Bright Data Web Unlocker 재사용
> 5. APScheduler in-process (FastAPI lifespan)

## 🧭 핵심 설계 결정 (Phase 1 진입 전 확정)

> **결정 1 — ranking 도메인의 SERP 호출 방식**
> ⚠️ `architecture-check.sh` 의 `STAGE_ORDER` 는 `crawler=1`, `analysis=2`, ... 로 정의되어 있고 새 도메인 `ranking` 이 `crawler` 를 직접 import 하면 동급 교차로 차단된다.
> **선택지 A (채택)**: `ranking` 을 `STAGE_ORDER[ranking]=0` 격리 도메인으로 등록 + 의존성 주입.
> - `domain/ranking/tracker.py` 가 `Callable[[str], str]` (URL → HTML) 타입의 `serp_fetcher` 를 인자로 받음
> - 실제 `BrightDataClient.fetch` 주입은 `application/ranking_orchestrator.py` 에서 수행
> - `domain/ranking/*.py` 는 `domain.crawler` 를 절대 import 하지 않음 (DAG 격리 유지)
> - 단, `domain.crawler.serp_collector._parse_serp_html` 같은 파서 헬퍼는 **재구현하지 않고 application 이 호출해 ranking 에 결과만 전달**
>
> **결정 2 — 매칭 로직 위치**
> "내 publication URL 이 SERP 에 있는가?" 매칭은 ranking 의 책임. publication URL 을 `m.blog.naver.com` 정규화 + `_normalize_href` 와 동일한 정규식으로 후보 URL 정규화 후 동등 비교. (SPEC-SEO-TEXT.md §3 [1] BLOG_POST_URL_RE 와 동일 패턴 — `domain/ranking/url_match.py` 에 재정의, regex 상수만 복제)
>
> **결정 3 — 스케줄러 단위**
> APScheduler `AsyncIOScheduler` 사용 (FastAPI 가 이미 asyncio loop 가 있음). job 함수는 동기지만 `run_in_executor` 로 위임. 단일 인스턴스 전제 (이중 실행 방지 락은 Phase 2)

---

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase R1~R7 순위 추적 시스템 MVP) -->

## ⚠️ 위험 요소 (Risk Register)

### Risk-R1: ranking → crawler 도메인 의존성
- **현상**: `domain/ranking/tracker.py` 가 `domain/crawler/serp_collector.py` 의 함수를 import 하면 `architecture-check.sh` 의 DAG 검사가 차단 (수평 교차)
- **완화**: 채택안 = 의존성 주입. ranking 은 `Callable` 만 받고, 실제 BrightDataClient 주입은 application 레이어가 수행. STAGE_ORDER 에 `[ranking]=0` 등록해 격리 도메인으로 명시
- **잔존 리스크**: BLOG_POST_URL_RE 정규식이 두 곳 (serp_collector + ranking/url_match) 에 복제됨 → serp_collector 변경 시 ranking 동기화 누락 가능
- **모니터링**: lessons.md 에 명시 + 양쪽 파일 상단 주석에 "동기화 대상" 표기

### Risk-R2: Supabase 마이그레이션 실패 롤백
- **현상**: `publications` / `ranking_snapshots` 생성 SQL 실행 중 권한 오류 또는 FK 충돌
- **완화 절차**:
  1. 마이그레이션 전 Supabase 대시보드에서 기존 schema export (백업)
  2. 새 테이블 SQL 만 분리해 실행 (기존 pattern_cards/generated_contents 영향 X)
  3. 실패 시 `drop table if exists ranking_snapshots; drop table if exists publications;` 로 청소 후 재시도
- **잔존 리스크**: cascade delete 가 publication 삭제 시 snapshots 일괄 삭제 → 의도 맞지만 명시 필요

### Risk-R3: APScheduler 재시작 시 잡 손실/중복
- **현상**: in-process AsyncIOScheduler 는 영속 저장소 없음. uvicorn 재시작 시 09:00 KST 직전 재시작되면 누락, 직후 재시작되면 중복 트리거 가능
- **완화**: `coalesce=True` (밀린 잡 1회로 합침) + `max_instances=1` (동시 1개) 설정. 멀티 인스턴스 배포는 SPEC 범위 밖 (1 인스턴스 전제)
- **잔존 리스크**: Render.com 같은 스케일링 환경에서 인스턴스 2개 이상 시 중복 호출 → 추후 Postgres advisory lock 또는 Redis lock 필요. 본 MVP 에서는 lessons.md 에 경고만

### Risk-R4: Bright Data 비용
- **현상**: 매일 모든 publication SERP 1회 호출. 100개 publication 시 월 3000회 추가
- **추정**: Web Unlocker 1회당 약 $0.001~$0.003 (zone 요금제 기준) → 100 publication × 30일 × $0.002 ≈ **월 $6**. 1000 publication 이면 월 $60
- **완화**: (1) 7일 이상 100위 밖 publication 자동 비활성화 (Phase 2), (2) `application/usage_tracker.py` 에 ranking 호출 카운트 추가, (3) settings 에 `ranking_max_publications_per_check: int = 200` 가드
- **잔존 리스크**: SERP 트래픽 폭증 시 Bright Data zone rate limit 트리거. R2.1.3 의 1초 sleep 으로 완화

### Risk-R5: 도입부 톤 락 / 의료법 무관성
- **현상**: ranking 은 콘텐츠 생성·수정 X → M2 톤 락, compliance 3중 방어 무관
- **확인**: 본 작업 중 `domain/generation/`, `domain/compliance/`, `body_writer.py` 어떤 파일도 수정 X. post-edit-lint.sh / seo-writer-guardian 트리거 0회

### Risk-R6: 프론트엔드 인증 헤더
- **현상**: 최근 cef20ff 커밋에서 UsageDashboard 가 직접 origin 호출 + 인증 헤더 전환. ranking 컴포넌트도 동일 패턴 따라가야 함
- **완화**: R5.1.2 에서 `lib/api.ts` 의 기존 fetcher 만 사용. 직접 fetch 금지

---

# UI 세로 스크롤 압축 (PC 우선) — 2026-04-27 착수

> 목표: PC 1920×1080 화면에서 모든 페이지의 세로 스크롤 최소화. 캘린더 키워드 증가 대응 핵심.
> 사용자 결정: C안(행/열 전치) 제외. 순차 진행.

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase U0~U12) -->

---

# 키워드 배치 운영 시스템 (Batch Pipeline) MVP — 2026-05-04 착수

> 목표: 100개 이상 키워드를 CSV 1회 업로드로 자동 처리. 단일 흐름 100% 보존.
> SPEC 참조: SPEC-BATCH.md (전체 명세)
> CLAUDE 규칙 준수: additive only, 단일 함수 시그니처 불변, Pydantic 반환, semaphore 단일 프로세스 명시
>
> 사용자 결정 (불변, 4 라운드 검토 완료):
> 1. 단일 흐름 변경 0 — `application/orchestrator.py` 4 함수 그대로
> 2. Phase 1 = `mode=now` 만 처리, `overnight`/`auto` 는 DB/API 받되 `400 Not Supported Yet`
> 3. UI default operation = `analyze` (pipeline 명시 선택)
> 4. PatternCard 모델 무수정 (재사용은 batch_item 컬럼만)
> 5. FK nullable, Phase 1 은 `(job_id, slug, keyword)` triple link
> 6. 클러스터링은 수동 (`cluster_id` + `cluster_role` CSV 컬럼)
> 7. 단일 web process 전제, 멀티 워커는 Phase 3+

## 🧭 핵심 설계 결정 (Phase 1 진입 전 확정)

> **결정 1 — `domain/batch` 격리 도메인 등록**
> `architecture-check.sh` 의 `STAGE_ORDER[batch]=0` 추가. `domain/batch` 는 다른 도메인 import 금지. `application/batch_orchestrator` 가 `domain/batch` + `application.orchestrator` 합성.
>
> **결정 2 — `BatchJobManager` 분리 (in-process MVP)**
> 단일 `JobManager`(MAX_WORKERS=2) 와 별도. `BATCH_MAX_WORKERS=2~3` env. Phase 3 부터 worker process 분리.
>
> **결정 3 — BrightData semaphore 단일 프로세스 안전망**
> `domain/crawler/brightdata_client.py` module-level `Semaphore(BRIGHTDATA_CONCURRENT_LIMIT, default 5)`. 멀티 워커 진입 시 Redis advisory lock 으로 교체 (Phase 3+).
>
> **결정 4 — Phase 1 상태 머신 단순화**
> `queued → running → succeeded / needs_review / failed` (+ `skipped` Phase 2). `analyzing/ready_to_generate/generating` 은 dead state 회피 위해 Phase 2 활성.

---

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase B1~B6 Batch Pipeline MVP — stale 체크박스, 후속 PR B7~B19 로 완료 검증) -->

## ⚠️ 위험 요소 (Risk Register — Phase 1)

> SPEC-BATCH.md §9 의 B1~B8 참조. Phase 1 시점 가장 큰 리스크:
>
> - **B1 (full pipeline 실수)**: UI default `analyze`. CLI 도 `--operation analyze` 가 default. `pipeline` 은 명시 필요.
> - **B2 (BrightData rate)**: semaphore default 5. 단일 호출과 합산 제한. 100건 batch 진행 중 단일 `/api/jobs` 호출이 503 안 받는지 통합 smoke 로 검증 (B6.5).
> - **B5 (in-memory worker)**: deploy/restart 시 진행 중 item 은 DB 에 `running` 으로 남음. Phase 1 보호: 시작 시 `running` 상태이고 30분 이상 갱신 없는 item 은 자동 `queued` 복귀 (orchestrator startup hook).
> - **B6 (FK 못 채움)**: Phase 1 은 `(job_id, slug, keyword)` triple link 만. 검수 큐 (Phase 2) 시 join 으로 generated_contents 회수.

---

## 🔮 Phase 2~4 (요약, 별도 todo 섹션 진입 시 분해)

> 각 Phase 는 SPEC-BATCH.md §3 의 Phase 2/3/4 정의 참조. Phase 1 그린 + 운영 1주 후 진입.

- **Phase 2 (3~4일)** — 사전 필터, cluster 재사용, 검수 큐, FK 정합성 보강
- **Phase 3 (3~4일)** — Anthropic Batch API adapter (LLM 독립 호출 한정), worker process 분리
- **Phase 4 (2~3일)** — Slack 알림, publication 자동 등록 (opt-in)

---

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase B7~B19 Batch Pipeline) -->

---

# Title Validator (HTML title 검증/템플릿) — Plan

> 2026-05-06 착수. SPEC-SEO-TEXT.md §3 [6] + docs/naver-seo-guide.md §2.2 / §4. Layer 1 품질 강제 라인 (outline_validator) 의 자매 검증 모듈.
> 2026-05-06 갱신: 사용자 확정 결정 6건 반영 (재생성 전략 B / strict env 토글 / 스팸 모듈 상수 / 길이 hard+권장 분기 / exact match / Slack 보류).

## 🔴 핵심 원칙 (모든 step 의 상위 가이드)

> **"제목은 고치되 intro 톤 락은 절대 흔들지 않는다."**
> **본 모듈은 title quality gate 이지 LLM fixer 시스템이 아니다.**
>
> - 신규 prompt builder / 신규 tool_use 스키마 / title 단독 LLM helper — **모두 금지**
> - 추가 LLM 호출은 outline 재생성 1회뿐. title 만 따로 재생성하지 않음
> - intro 톤 락 보존은 코드(programmatic) 덮어쓰기로만 달성 (LLM 호출 0회)
> - 구현 범위가 LLM 호출을 늘리거나 새 프롬프트를 만드는 방향으로 가면 잘못된 것

## 배경 (3줄)

본 프로젝트의 출력은 네이버 스마트에디터 붙여넣기용 본문 HTML 이며, composer 화이트리스트가 `<head>` 메타를 전부 제거하기 때문에 `<title>` 태그 자체는 SERP 에 반영되지 않는다. 그러나 `Outline.title` 은 사용자가 네이버 에디터의 "제목" 입력란에 직접 복사하는 **단일 출처**이므로, [6] 아웃라인 생성 직후가 품질 검증의 유일한 지점이다. 네이버 가이드 (콘텐츠 작성 권장사항) 가 명시한 "잦은 제목 변경, 과도한 길이, 2회 이상 반복 키워드, 스팸성/홍보 문구" 4 항목을 코드로 검증하고, 의료법 단일 출처 (`domain/compliance/rules.py`) 를 재사용해 새 위반 생성을 차단한다.

## 변경 대상 파일

| 파일 | 변경 종류 | 책임 |
|---|---|---|
| `domain/generation/title_validator.py` | **신규** | 제목 검증 진입점 + Pydantic 모델 + 스팸 모듈 상수 |
| `tests/test_generation/test_title_validator.py` | **신규** | 단위 테스트 (총 19~20 케이스) |
| `application/stage_runner.py` `run_stage_outline_generation` | **수정** | outline_validator 와 동일 패턴으로 1회 재생성 통합 + intro 코드 덮어쓰기 |
| `config/settings.py` | **수정** | `title_validator_strict_compliance: bool = False` 필드 추가 |
| `tasks/todo.md` (본 섹션) | **수정** | 진행 추적 |
| `tasks/lessons.md` | **(선택)** | 의사결정 핵심 1건 기록 (예: title gate 와 fixer 의 경계) |

명시적으로 **수정하지 않는** 파일:
- `domain/generation/model.py` — `Outline.title` 시그니처 무변경 (단일 출처 유지)
- `domain/generation/outline_writer.py` — 검증은 호출 측 (stage_runner) 에서. writer 는 순수 생성만
- `domain/generation/outline_validator.py` — title 검증 통합하지 않고 자매 모듈로 분리 (사유: outline_validator 는 "구조" 검증, title_validator 는 "텍스트 품질" 검증으로 책임 분리)
- `domain/compliance/rules.py` — 단일 출처 무변경. **카테고리 추가/스팸 패턴 추가 금지** (의료 도메인 정의 외 일반 SEO 품질 규칙은 검증기 자체 보유)
- `domain/composer/naver_html.py` — `<title>` 은 본문 복사 대상 아니므로 SERP 영향 없음. 템플릿 변경 안 함
- `domain/generation/CLAUDE.md` — 본 모듈은 "검증" 이지 "생성" 이 아니므로 가드 문서 갱신 대상 아님
- `application/notifier.py` / Slack webhook — Phase 4 notifier 연결은 **본 plan 보류** (후속 PR)

## 구현 단계 (체크리스트)

- [ ] **Step 1**: `domain/generation/title_validator.py` 신규 — `TitleIssue` (dataclass, `severity: Literal["error","warning"]` 필드 포함) + `TitleValidationReport` (Pydantic) 모델 정의 + 빈 `validate_title(outline, primary_keyword, *, strict_compliance: bool) -> TitleValidationReport` 골격. 의존: `Outline`, `domain.compliance.rules.get_all_patterns(SEO_STRICT)` import. **`severity="error"` 만 재생성 트리거 / `"warning"` 은 logger 만**. (~30분)
- [ ] **Step 2**: 길이 검증 helper `_check_length(title) -> TitleIssue | None`. 임계값 모듈 상수: `_TITLE_HARD_MIN=20`, `_TITLE_RECOMMEND_MIN=25`, `_TITLE_RECOMMEND_MAX=35`, `_TITLE_HARD_MAX=40`. 분기:
  - `len < 20` 또는 `len > 40` → `severity="error"` (hard fail, 재생성)
  - `20 <= len < 25` 또는 `35 < len <= 40` → `severity="warning"` (logger 만)
  - `25 <= len <= 35` → 통과 (issue 없음)
  - CLAUDE.md "임계값/매직 넘버는 상수 모듈로 승격" 준수. (~30분)
- [ ] **Step 3**: 키워드 반복 검증 helper `_check_keyword_repetition(title, primary_keyword) -> TitleIssue | None`. **normalized exact match 만**: 대소문자 lower + 연속 공백 단일화 후 `normalized_title.count(normalized_keyword) >= 2` 면 `severity="error"`. `primary_keyword` 가 None/빈 문자열이면 검증 스킵. **부분 매치 / 형태소 분석 / 공백 변형 ("다이어트한의원" vs "다이어트 한의원") 은 본 plan 범위 외 (OUT-OF-SCOPE — 후속 PR)**. (~30분)
- [ ] **Step 4**: 스팸/장식 표현 검증 helper `_check_spam(title) -> list[TitleIssue]`. **`title_validator.py` 자체 모듈 상수**:
  - `_TITLE_SPAM_LITERALS = ("필독", "초강추", "대박", "진짜", "핫이슈", "클릭", ...)` — 단순 literal 매치
  - `_TITLE_SPAM_PATTERNS = (re.compile(r"!{3,}"), re.compile(r"[★♥]"), re.compile(r"~{2,}"), re.compile(r"\?{2,}"), re.compile(r"(이모지 범위 regex)"), ...)` — 정규식 매치
  - 위치 결정 사유: 의료 도메인 의존이 아닌 도메인 독립 품질 규칙. compliance/rules.py 카테고리 추가는 SPEC 2개 + 5개 파일 동시 수정 의무 동반 → 본 plan 범위 폭증 회피. **단일 출처 원칙은 "의료법 카테고리"에 한정**, 일반 SEO 품질 규칙은 검증기 자체 보유 가능
  - 모든 스팸 위반은 `severity="error"` (strict 토글 무관 항상 hard fail). (~45분)
- [ ] **Step 5**: 의료법 금지 표현 검증 helper `_check_compliance(title, *, strict: bool) -> list[TitleIssue]`. `get_all_patterns(CompliancePolicy.SEO_STRICT)` 로 컴파일된 regex 목록 → 매치 카테고리 전부 issue 화. **strict 분기**:
  - `strict=True` → `severity="error"` (재생성 트리거)
  - `strict=False` (default) → `severity="warning"` (logger.warning 만, **재생성 트리거 안 함**, `passed=True` 유지)
  - env 변수 `TITLE_VALIDATOR_STRICT_COMPLIANCE` (default `false`) 를 `config/settings.py` 의 `title_validator_strict_compliance: bool = False` 필드로 노출
  - **rules.py 외부에 패턴 하드코딩 절대 금지** (compliance/CLAUDE.md 단일 출처 원칙 — 의료 카테고리는 항상 rules.py 만 참조). (~45분)
- [ ] **Step 6**: `validate_title()` 본체 — 위 4종 helper (`_check_length`, `_check_keyword_repetition`, `_check_spam`, `_check_compliance`) 차례로 호출, 모든 issue 수집. `passed` 계산: **`severity="error"` 가 1개라도 있으면 `passed=False`**. warning 만 있으면 `passed=True` (재생성 트리거 안 함). suggestions 는 빈 리스트 유지 (YAGNI). (~30분)
- [ ] **Step 7**: `application/stage_runner.py` `run_stage_outline_generation` 통합 — **재생성 전략 = B (통째 재생성 + intro 덮어쓰기)**:
  - 기존 `validate_outline` 호출 직후 `validate_title(outline, pattern_card.keyword, strict_compliance=settings.title_validator_strict_compliance)` 추가
  - 두 검증 결과를 합쳐 **1회 재생성** (LLM 비용 최소화)
  - 재생성 호출은 기존과 동일한 `generate_outline(pattern_card, compliance_rules, feedback=...)`
  - **재생성 후 intro 만 코드 덮어쓰기**: `replaced_outline.intro_md = old_outline.intro_md` (programmatic, LLM 호출 0회). helper `_replace_intro(new_outline: Outline, old_intro_md: str) -> Outline` 추가
  - sections / image_prompts 는 재생성된 새 값 사용 (새 title 과 잘 맞을 가능성)
  - feedback 문자열 합성 시 outline issues / title issues (severity=error 만) 구분된 섹션으로 표기
  - 재생성 후에도 title issue 가 남으면 logger.warning 만 (3계층 시스템 일관성)
  - **title 단독 LLM helper / 신규 프롬프트 빌더 / 신규 tool_use 스키마 — 모두 금지** (핵심 원칙). (~1시간)
- [ ] **Step 8**: `config/settings.py` — `title_validator_strict_compliance: bool = False` 필드 추가. env 변수 매핑 `TITLE_VALIDATOR_STRICT_COMPLIANCE`. Pydantic settings 패턴 기존 필드 따름. (~15분)
- [ ] **Step 9**: `tests/test_generation/test_title_validator.py` 신규 — 아래 "테스트 케이스" 19~20개 작성. `_make_outline_with_title()` 헬퍼로 minimal `Outline` 인스턴스 생성. (~1시간 30분)
- [ ] **Step 10**: 검증 — `pytest tests/test_generation/test_title_validator.py --no-cov` 그린, `pytest tests/test_generation/test_outline_validator.py --no-cov` regression 그린, `pytest tests/test_application --no-cov` (stage_runner 영향 검증) 그린, `bash .claude/hooks/build-check-fast.sh` 클린. (~30분)
- [ ] **Step 11**: 최종 게이트 — `bash .claude/hooks/build-check.sh` 그린 (커버리지 포함). 통과 시 commit `feat(generation): HTML title 검증 (길이/반복/스팸/의료법)` 안 (사용자 승인 후 실제 commit). (~30분)

총 예상: 7~8시간 (Step 7 의 intro 덮어쓰기 helper + Step 9 의 테스트 작성이 가장 무거움).

## 검증 항목 상세

### 1. 길이 (`length`)
- **hard fail (error, 재생성)**: `< 20자` 또는 `> 40자`
- **권장 범위 외 (warning, logger 만)**: `20~24자`, `36~40자`
- **정상**: `25~35자`
- 사유: 네이버 SERP PC ~30자, 모바일 ~25자에서 잘림. 의료 정보성 키워드 일부가 25 미만으로 자연스러울 수 있어 hard fail 은 20 까지 완화. 40 초과는 가독성 손실 확정

### 2. 키워드 반복 (`keyword_repetition`)
- `pattern_card.keyword` 를 primary keyword 로 받음 (stage_runner 가 전달)
- **normalized exact match 만**: 대소문자 lower + 연속 공백 단일화 후 `count() >= 2` 면 위반 (`severity="error"`)
- 부분 매치 / 형태소 분석 / 공백 변형 — **OUT-OF-SCOPE** (후속 PR)
- 빈 키워드 / None → 검증 스킵 (graceful)

### 3. 스팸/장식 표현 (`spam`)
- **위치**: `title_validator.py` 자체 모듈 상수 `_TITLE_SPAM_LITERALS` / `_TITLE_SPAM_PATTERNS`
- 위반 시 항상 `severity="error"` (strict 토글 무관)
- compliance/rules.py 변경 없음 (의료 카테고리 외 일반 품질 규칙)

### 4. 의료법 금지 표현 (`compliance`)
- `domain.compliance.rules.get_all_patterns(CompliancePolicy.SEO_STRICT)` 호출 → 10개 카테고리 regex
- **strict 토글 분기**:
  - `TITLE_VALIDATOR_STRICT_COMPLIANCE=true` → `severity="error"` (재생성 트리거)
  - default `false` → `severity="warning"` (logger 만, `passed=True` 유지)
- `rules.py` 외부에 패턴/금지표현 절대 하드코딩 금지 (post-edit-lint.sh 훅이 차단)

## 테스트 케이스 (총 19~20개)

`TestValidateTitle` 클래스 내부:

### 길이 (6개)
1. `test_passes_when_all_ok` — 28자 + 위반 없음 → `passed=True, issues=[]`
2. `test_fails_when_title_too_short_under_20` — 12자 → `length` error
3. `test_fails_when_title_too_long_over_40` — 45자 → `length` error
4. `test_warns_when_title_in_recommend_outer_22` — 22자 → `length` warning, `passed=True`
5. `test_warns_when_title_in_recommend_outer_38` — 38자 → `length` warning, `passed=True`
6. `test_passes_at_recommend_boundary_25_and_35` — 정확히 25자 / 35자 → 통과

### 키워드 반복 (3개)
7. `test_fails_when_primary_keyword_repeats_twice` — "탈모치료 가이드 - 탈모치료 핵심" → `keyword_repetition` error
8. `test_passes_when_primary_keyword_appears_once` — "탈모치료 핵심 가이드 정리" → 통과
9. `test_skips_repetition_check_when_keyword_empty` — primary_keyword=None → issue 없음

### 스팸 / 장식 (3개)
10. `test_fails_when_title_contains_spam_literal` — "필독! 탈모치료 핵심 가이드" → `spam` error
11. `test_fails_when_title_contains_excessive_exclamation` — "탈모치료 가이드!!!" → `spam` error (`!{3,}` 패턴)
12. `test_fails_when_title_contains_decorative_chars` — "★ 탈모치료 핵심 정리 ★" → `spam` error

### 의료법 strict 토글 (2개)
13. `test_warns_compliance_when_strict_off` — "100% 효과 보장 탈모치료 정리" + `strict_compliance=False` → `compliance` warning, `passed=True`
14. `test_fails_compliance_when_strict_on` — 동일 title + `strict_compliance=True` → `compliance` error, `passed=False`

### 다중 issue 동시 수집 (1개)
15. `test_collects_multiple_issues_simultaneously` — 길이 위반 + 키워드 반복 + 스팸 → 모든 issue 수집 (short-circuit 안 함)

### intro 보존 회귀 (1개) — stage_runner 통합 테스트
16. `test_intro_preserved_after_outline_regeneration` — Mock `generate_outline` 으로 1차→2차 다른 intro 반환 / title issue 1차에서 발생 / 2차 outline 의 `intro_md` 가 1차 값으로 덮어써졌는지 확인 (M2 톤 락 회귀)

### 단일 출처 / 케이스 (2~3개)
17. `test_keyword_repetition_normalized_case` — primary "Hair" + title 내 "HAIR ... hair" → 위반
18. `test_compliance_via_rules_module_only` — monkeypatch 로 `rules.RULES` 비우면 compliance issue 0
19. `test_validate_title_passes_with_only_warnings` — warning 만 다수 / error 없음 → `passed=True`

선택 (시간 여유 시):
20. `test_settings_default_strict_compliance_is_false` — `config/settings.py` 의 default 회귀

## 위험 요소 / 결정 필요 사항

1. **(✅ 결정 — 길이)** 20~40 hard fail / 25~35 권장 (warning) / 20~24·36~40 warning. severity 분기로 구현
2. **(✅ 결정 — 키워드 반복)** normalized exact match 만. 부분 매치 / 형태소 / 공백 변형 OUT-OF-SCOPE
3. **(✅ 결정 — 재생성 정책)** B (outline 통째 재생성 + intro 코드 덮어쓰기). title 단독 LLM helper 금지
4. **(✅ 결정 — compliance false positive)** env 토글 `TITLE_VALIDATOR_STRICT_COMPLIANCE` default `false`. False → warning + `passed=True`. True → error + 재생성
5. **(✅ 결정 — 스팸 검증)** 본 plan 포함. `title_validator.py` 자체 모듈 상수. compliance/rules.py 변경 없음
6. **(✅ 결정 — Slack notifier)** 본 plan 보류. logger.warning + 테스트만. 후속 PR 에서 별도 plan
7. **(잔존 리스크) primary_keyword 의 전달 경로**: `pattern_card.keyword` 가 항상 채워진다는 가정. `tests/test_outline_validator.py` 의 `_make_pattern_card` 가 `keyword="테스트"` 명시 → 안전
8. **(잔존 리스크) Pydantic 모델 정의 위치**: `TitleValidationReport` 는 `domain/generation/title_validator.py` 안. outline_validator.py 의 `OutlineIssue` 자매 패턴 일관성. model.py 는 "도메인 출력", validator report 는 "검증 결과" 분리
9. **(잔존 리스크) intro 덮어쓰기와 sections 정합성**: 새 title 에 맞춰 sections 가 바뀌었는데 intro 만 옛 값이면 어긋날 가능성. 완화: intro 는 도입부(200~300자) 톤 락이라 sections 와 직접 의존 약함. 어긋남 발생 시 운영 데이터로 후속 PR

## 본 plan 에서 명시적으로 제외한 것 (OUT-OF-SCOPE)

- **title 단독 LLM helper / 신규 prompt builder / 신규 tool_use 스키마** — 핵심 원칙 위반 (LLM 호출 추가 금지)
- **자동 수정 (fixer)** — 본 plan 은 quality gate, fixer 아님. 위반은 outline 재생성 1회 + warning 만
- **부분 매치 / 형태소 분석 / 공백 변형 키워드 반복** — 후속 PR 에서 형태소 분석기 도입 시 별도 plan
- **의료법 카테고리 추가 / `domain/compliance/rules.py` 변경** — 스팸 규칙은 `title_validator.py` 자체 보유. 단일 출처 원칙은 의료 카테고리에 한정
- **Slack notifier / Phase 4 알림 연결** — `logger.warning` 만으로 충분. 후속 PR 에서 "재생성 실패 / strict fail" 운영 이벤트 별도 plan
- **Meta description / og:* / JSON-LD / canonical 생성** — naver-seo-guide.md "Top 5" 의 #1·#3·#4 별도 plan
- **composer 의 `<title>` 템플릿 변경** — `<title>` 은 본문 복사 대상 아니므로 SERP 영향 없음
- **title 전용 compliance 화이트리스트** — strict default false 로 false positive 영향 최소화. 운영 데이터 누적 후 후속 PR
- **regression 테스트 fixture 추가 (실측 HTML 기반)** — 본 plan 은 단위 테스트 + intro 보존 회귀 1건만

---

# UX Refactor — Operations OS 정렬 (6 Phase 풀패키지)

> 2026-05-06 착수. 사용자 확정 결정 4건 (운영 홈 / `/create` 통합 / `/queue` 통합 / 라벨 매핑) 반영.
> 2026-05-06 갱신. 사용자 확정 결정 5건 + plan-reviewer 보완 5건 반영. P1 즉시 시작 가능.
> 백엔드는 이미 운영 OS 구조 (`application/operations_home.py` 4 큐 + workflow_status FSM). UI 가 못 따라온 상태를 정렬한다.
> 총 22 일 예상 (P2 5일→4일 압축). 단계 별 검증 게이트 통과 시에만 다음 Phase 진입.

## 🟢 P1 즉시 시작 가능 (사용자 결정 완료)

기존 "사용자 답변 받기 전 진행 불가" 블로커 5건 모두 ✅ 처리됨:

1. ✅ **`/pipeline` 처리** = `/` 로 redirect (P1 Step 1.3-bis). nav "생성" 항목은 `/create` (P4 신설) 만 가리킴. 사용자 의도 (단계별 흐름 시각화) 는 운영 홈 안 섹션으로 보존.
2. ✅ **lucide-react 도입** = 확정. P2 Step 2.0 에서 `web/frontend/package.json` 의존 추가.
3. ✅ **P5 데이터 소스** = frontend merge 확정. 백엔드 `application/unified_queue.py` 신설 안 함 (운영 규모 1000 row 미만).
4. ✅ **vitest 라벨 매칭 영향** = 0건 (현재 18 vitest 의 텍스트 매칭은 라벨 매핑과 무관). P3 Step 추가: 신규 StatusBadge 도입 시 vitest 는 labels.ts 함수 호출 결과로 매칭.
5. ✅ **공지 = 안 함 + README 1줄** = `web/README.md` 또는 `CLAUDE.md` 변경 이력에 1줄 추가 (P1 종료 step). 별도 in-app 배너 X.

## 🔴 핵심 원칙 (전 Phase 공통)

- **단일 흐름 시그니처 절대 무변경** — `application/orchestrator.py` 의 `run_pipeline / run_analyze_only / run_generate_only / run_validate_only` 4 함수, `application/operations_home.py`, `application/batch_orchestrator.py`, `application/auto_publisher.py` 시그니처 손대지 않는다 (`@project_seo_operating_philosophy.md` 위반 차단)
- **web/api 라우터 시그니처 무변경** — 기존 엔드포인트는 그대로. UX 리팩터는 frontend 만
- **DB enum 무변경** — `workflow_status`, `visibility_status`, `batch_item_status` 마이그레이션 X. **UI 라벨 매핑 함수만** 추가
- **Next.js 16 경고 준수** — `web/frontend/AGENTS.md` "This is NOT the Next.js you know". 새 API 사용 시 반드시 `node_modules/next/dist/docs/` 확인 후 코딩
- **이모지 금지** — `feedback_no_emoji.md` 메모리 준수. 본 plan 작성·UI 카피·코드 모두 이모지 X
- **additive 우선** — Phase 2 컴포넌트 추가 후 Phase 3~5 가 기존 컴포넌트를 점진 교체. 한 번에 다 바꾸지 않음
- **각 Phase 종료 시 데모 가능** — 사용자 보고 후 다음 Phase 진입

## 🔴 절대 금지 (전 Phase)

- 백엔드 use case 시그니처 변경 (orchestrator.py / operations_home.py / batch_orchestrator.py)
- DB enum 변경 / Supabase migration
- compliance/rules.py 변경
- needs_review 자동 폐기 (운영 철학: 후보 키워드 = 전부 발행 대상)
- 단일 PR 에서 2 Phase 이상 묶음 (검증 게이트 누락 위험)

## Phase 1 — Nav 정리 + 운영 홈 승격 (2일)

목표: nav 9개 → 6 영역 재편. `/` 가 운영 홈 (현재 `/rankings` 컨텐츠) 으로 승격. 기존 `/` 의 단일 작업 입력 + Job 모니터링은 임시 보존 영역으로 이동. 외부 링크는 redirect 로 보호.

### 변경 대상 파일

| 파일 | 변경 종류 |
|---|---|
| `web/frontend/src/app/layout.tsx` | nav 항목 재편, 6 영역 + active 표시 |
| `web/frontend/src/app/page.tsx` | 운영 홈 컨텐츠로 교체 (`/rankings/page.tsx` 컨텐츠 이전) |
| `web/frontend/src/app/rankings/page.tsx` | redirect 어댑터 (`/` 로 영구 redirect) |
| `web/frontend/src/app/pipeline/page.tsx` | redirect 어댑터 (`/` 로 영구 redirect) <!-- 2026-05-06 추가 --> |
| `web/frontend/src/app/legacy-jobs/page.tsx` | 신규 — 기존 `/` 의 NewJobForm + JobList + ResultsArchive 임시 보존 (Phase 4 에서 정리) |
| `web/frontend/src/components/__tests__/NavBar.test.tsx` | 신규 — 6 메뉴 렌더링 + active state 회귀 |
| `web/README.md` 또는 `CLAUDE.md` 변경 이력 | 1줄 추가 — UX 리팩토링 시작 + `/legacy-jobs` 임시 보존 안내 <!-- 2026-05-06 추가 --> |

### 6 영역 매핑 (확정) <!-- 2026-05-06 갱신: nav 라벨/path 모순 해결 -->

| nav 라벨 | 경로 | 비고 |
|---|---|---|
| 운영 홈 | `/` | 현재 `/rankings` 본체 (운영 OS 메인) + `/pipeline` 의 단계별 흐름 섹션 흡수 |
| 생성 | `/legacy-jobs` (P1) → `/create` (P4 신설) | P1 단계는 기존 NewJobForm 임시 보존, P4 에서 통합 페이지 신설 |
| 검수·발행 | `/batches` (P1) → `/queue` (P5 신설) | P1 단계는 기존 batches 그대로 |
| 성과·분석 | `/insights` | drawer: 향후 통합 검토 |
| 브랜드 | `/brand-studio` | 그대로 |
| 관리 | `/usage` | drawer: `/keywords` (난이도) |

**중요**: `/pipeline` 은 어떤 nav 에도 직접 link 안 함. P1 시점에 `/` 로 영구 redirect. 사용자 의도 (단계별 흐름 시각화) 는 운영 홈 안 별도 섹션으로 흡수 (P1 plan 내 P3·P5 후속 검토).

### 구현 단계 (체크리스트)

- [ ] **Step 1.1**: `web/frontend/src/app/page.tsx` 의 현재 컨텐츠 (NewJobForm + JobList + ResultsArchive) 를 `app/legacy-jobs/page.tsx` 로 이동. import 경로 그대로 동작 확인 (`pnpm --filter ./web/frontend dev` 띄우고 `/legacy-jobs` 진입). 검증: 단일 작업 제출 1회 + Job 목록 polling 동작
- [ ] **Step 1.2**: `web/frontend/src/app/rankings/page.tsx` 의 컨텐츠를 `web/frontend/src/app/page.tsx` 로 이동 (default export 함수 이름 `OperationsHomePage` 유지). 검증: `/` 진입 시 운영 홈 카드 + 4 큐 탭 + 240여 row 정상 렌더링
- [ ] **Step 1.3**: `web/frontend/src/app/rankings/page.tsx` 를 redirect 어댑터로 교체. Next.js 16 redirect 방식: `import { redirect } from "next/navigation"; export default function Page() { redirect("/"); }`. **선결 조건**: `node_modules/next/dist/docs/` 에서 redirect API 가 P1 시점 Next 16 에서 stable 인지 1회 확인. 검증: `/rankings` 입력 시 `/` 로 즉시 이동
- [ ] **Step 1.3-bis**: `web/frontend/src/app/pipeline/page.tsx` 를 redirect 어댑터로 교체 (`/` 로 영구 redirect). Step 1.3 과 동일 패턴. <!-- 2026-05-06 추가: `/pipeline` 처리 결정 (사용자 확정 5건 #1) --> 사용자 의도 (단계별 흐름 시각화) 는 운영 홈 안 별도 섹션 또는 P5 의 `/queue` MetricStrip 으로 흡수 (P3·P5 후속 검토). 검증: `/pipeline` 입력 시 `/` 로 즉시 이동
- [ ] **Step 1.4**: `web/frontend/src/app/layout.tsx` 의 nav 9개 → 6개로 재편. 헤더 라벨/path 매핑은 위 표 그대로 (`생성 → /legacy-jobs`, P4 에서 `/create` 로 변경). `/pipeline` 은 어떤 nav 에도 link 안 함. `usePathname()` 으로 active 표시 (active 시 `text-blue-700 font-semibold`, 그 외 `text-gray-700`). 검증: 6 메뉴 클릭으로 모두 진입 가능 + active 라벨 1개만 강조
- [ ] **Step 1.5**: `web/frontend/src/app/page.tsx` 상단의 "대시보드 ← 링크" (line 119) 제거. 운영 홈이 메인이므로 자기 자신 백링크 불필요. h1 라벨 "운영 홈" 유지
- [ ] **Step 1.6**: `web/frontend/src/components/__tests__/NavBar.test.tsx` 신규 — **P1 시점 시나리오 한정** <!-- 2026-05-06 갱신: plan-reviewer 보완 A --> — `/`, `/legacy-jobs`, `/batches`, `/insights`, `/brand-studio`, `/usage` 6개만 유효 클릭 단언. `/queue` 는 P5 까지 미존재이므로 nav 가 가리키지 않음 (P1 단언 대상 아님). usePathname 모킹 후 active state 클래스 단언. vitest 3건. (P5 후 후속 PR 에서 시나리오 갱신: `/`, `/create`, `/queue`, `/insights`, `/brand-studio`, `/usage`)
- [ ] **Step 1.7**: 임시 보존 표시 — `legacy-jobs/page.tsx` 상단에 "P4 통합 후 제거 예정" 문구 + nav 에서 P1 라벨 "생성" 이 가리킴 (P4 에서 `/create` 로 전환). 외부 링크 깨짐 방지 위해 `/jobs` 와 `/results/[slug]` 는 그대로 유지
- [ ] **Step 1.8**: README 1줄 추가 <!-- 2026-05-06 추가: 사용자 확정 5건 #5 --> — `web/README.md` (없으면 신규) 또는 `CLAUDE.md` 변경 이력에 1줄: "2026-05-06 UX 리팩토링 시작, 단일 작업 폼은 P4 까지 `/legacy-jobs` 임시 보존". 별도 in-app 배너·공지 채널 없음
- [ ] **Step 1.9**: 회귀 점검 — `pnpm --filter ./web/frontend test` (vitest) 통과, `pnpm --filter ./web/frontend tsc --noEmit` 통과

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린 (frontend tsc + vitest 포함)
- [ ] 6 메뉴 클릭으로 모두 진입 가능
- [ ] `/rankings` 진입 시 `/` 로 redirect 동작
- [ ] `/pipeline` 진입 시 `/` 로 redirect 동작 <!-- 2026-05-06 추가 -->
- [ ] `/legacy-jobs` 직접 입력 시 NewJobForm 정상 (P4 까지 가용)
- [ ] 기존 1296 pytest 회귀 0
- [ ] 사용자 데모 보고 — "Phase 1 완료, nav 정리 + 홈 승격 + redirect 안정"

### 데모 시나리오 (P1 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. `/` 진입 → 운영 홈 카드 + 4 큐 탭 (action_required / republishing / held / active) 정상 표시
2. nav 6 메뉴 (운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리) 클릭 → 모두 정상 진입
3. `/rankings` URL 입력 → `/` 로 redirect 확인
4. `/pipeline` URL 입력 → `/` 로 redirect 확인
5. `/legacy-jobs` URL 입력 → NewJobForm + JobList 정상 (P4 까지 임시 보존)
6. nav active state — 현재 페이지 라벨만 `text-blue-700 font-semibold` 강조

### 위험 요소

- **R1**: Next.js 16 의 redirect 가 client-side 가 아닌 RSC 환경에서 다르게 동작할 수 있음. 완화: Step 1.3 시작 전 `node_modules/next/dist/docs/` 확인 + `/rankings` 은 client component (`"use client"`) 가 아닌 server component 로 작성
- **R2**: layout.tsx active state 가 dynamic route (`/jobs/[id]`) 에서 깜빡일 가능성. 완화: usePathname 결과를 `startsWith("/jobs")` 로 매칭

---

## Phase 2 — 공통 화면 패턴 추출 (4일) <!-- 2026-05-06 갱신: plan-reviewer 보완 B (5일→4일 압축, Skeleton/ErrorBanner 는 P3/P5 시점 추가) -->

목표: 신규 `web/frontend/src/components/ui/` 폴더에 **8종 컴포넌트** 추가. <!-- 2026-05-06 갱신: plan-reviewer 보완 B — Skeleton.tsx 는 P5 (QueueItemDrawer lazy load), ErrorBanner.tsx 는 P3 (PublicationActionRow 마이그레이션) 시점에 추가 --> 기존 페이지 변경 X (additive only). Phase 3~5 가 점진 마이그레이션 시 사용.

### 신규 파일

| 파일 | 책임 |
|---|---|
| `components/ui/PageHeader.tsx` | 제목 + 부제 + 우측 액션 영역 슬롯 |
| `components/ui/StatusBadge.tsx` | `kind="workflow"\|"visibility"\|"difficulty"\|"compliance"\|"diagnosis"\|"batch"` + status → 색상/라벨 자동 매핑 |
| `components/ui/MetricStrip.tsx` | 운영 홈/배치 상단 카운트 카드 6~8개 (현재 `SummaryCards` 일반화) |
| `components/ui/DataTableShell.tsx` | sticky header + sort/filter 시그니처 + empty/error 슬롯 (loading 슬롯은 임시 inline div, P5 에서 Skeleton 으로 교체) |
| `components/ui/EmptyState.tsx` | icon (lucide-react) + title + description + CTA |
| `components/ui/ActionBar.tsx` | bulk action button row |
| `components/ui/Dialog.tsx` | overlay + ESC 닫기 + focus trap (현재 7개 dialog 가 wrapper 직접 작성) |
| `components/ui/Button.tsx` | `variant=primary\|secondary\|danger\|ghost` × `size=sm\|md` |
| ~~`components/ui/ErrorBanner.tsx`~~ | **P3 시점에 추가** (마이그레이션 중 필요 시) |
| ~~`components/ui/Skeleton.tsx`~~ | **P5 시점에 추가** (QueueItemDrawer lazy load 시) |
| `components/ui/__tests__/*.test.tsx` | 컴포넌트당 2~3건 vitest |
| `components/ui/index.ts` | barrel export |

### 구현 단계

- [ ] **Step 2.0** <!-- 2026-05-06 추가: 사용자 확정 5건 #2 — lucide-react 도입 확정 -->: `web/frontend/package.json` 에 `lucide-react` 의존 추가. `pnpm --filter ./web/frontend add lucide-react`. 검증: `import { ChevronDown } from "lucide-react"` 정상 import + tsc 통과. `pnpm-lock.yaml` 커밋 포함
- [ ] **Step 2.1**: `Button.tsx` — variant×size 매트릭스, disabled/loading prop. tests: primary 클릭, danger className, disabled 클릭 무시 (3건)
- [ ] **Step 2.2**: `Dialog.tsx` — `<dialog>` HTML 요소 또는 portal 결정 (Step 시작 전 결정). ESC 닫기, 외부 클릭 닫기, body scroll lock. tests: 열림/닫힘 콜백, ESC, focus return (3건)
- [ ] **Step 2.3**: `StatusBadge.tsx` — Phase 6 의 라벨 매핑 함수와 미리 통합 가능하도록 internal map. kind 별 색상 매트릭스 정의. tests: workflow="action_required" 빨강 클래스, visibility="off_radar" 로즈, batch="needs_review" 앰버 (3건)
- [ ] **Step 2.4**: `EmptyState.tsx` — lucide-react 의 `FileSearch`, `Inbox`, `AlertCircle` 등 사용 (Step 2.0 도입 완료 전제). tests: title/description 렌더링, CTA 클릭 (2건)
- [ ] **Step 2.5**: `MetricStrip.tsx` — props: `metrics: { label, value, color }[]`, grid responsive. 현재 `page.tsx` 의 `SummaryCards` 시그니처 그대로 받을 수 있게 설계. tests: 7 카드 렌더링, color prop 적용 (2건)
- [ ] **Step 2.6**: `DataTableShell.tsx` — 가장 복잡. sticky header, columns prop, sort callback, empty/error slot. **loading slot 은 임시 inline div** (P5 에서 Skeleton 도입 후 교체). 현재 `BatchProgressTable` / `BatchReviewQueue` 의 공통 추출 대상. tests: 빈 데이터 → empty slot, error → error slot, sort 클릭 콜백 (3건)
- [ ] **Step 2.7**: `PageHeader.tsx` + `ActionBar.tsx` — 단순 레이아웃. tests 각 2건
- [ ] **Step 2.8**: `index.ts` barrel export. `import { Button, Dialog } from "@/components/ui"` 형태로 사용 가능 확인
- [ ] **Step 2.9** <!-- 2026-05-06 추가: plan-reviewer 보완 C — 데모용 sample page -->: `app/_dev/ui/page.tsx` 신규 (개발용, nav 미연결, 직접 URL 만). 8 컴포넌트 사용 예시 1개씩. 사용자 데모 시 1 page 로 모두 확인 가능. robots/noindex meta 추가
- [ ] **Step 2.10**: 기존 페이지 변경 0 회귀 확인 — `pnpm --filter ./web/frontend tsc --noEmit` + `pnpm --filter ./web/frontend test`. 추가 ui 컴포넌트가 기존 import 와 충돌하지 않는지 확인

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] 신규 vitest 약 20건 (8 컴포넌트 × 평균 2.5건) 추가 + 통과 <!-- 2026-05-06 갱신: 25 → 20 -->
- [ ] 기존 18 vitest 회귀 0
- [ ] 기존 페이지 동작 시각 회귀 0 (스크린샷 비교는 안 함, 사용자 manual 확인)
- [ ] `app/_dev/ui` 진입 시 8 컴포넌트 sample 시각 확인
- [ ] 사용자 데모 보고 — "Phase 2 완료, ui 컴포넌트 라이브러리 가용. Phase 3 부터 점진 적용"

### 데모 시나리오 (P2 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. `/_dev/ui` 진입 → 8 컴포넌트 sample 모두 표시 (PageHeader / Button / Dialog / StatusBadge / MetricStrip / DataTableShell / EmptyState / ActionBar)
2. Button 4 variant × 2 size 매트릭스 시각 확인
3. Dialog 열기 → ESC 닫기 / 외부 클릭 닫기 동작
4. StatusBadge — workflow / visibility / batch 3 kind 의 status 별 색상 시각 확인
5. DataTableShell — 빈 데이터 / 에러 / 일반 데이터 3 case slot 표시
6. EmptyState — lucide-react 아이콘 정상 렌더링
7. 기존 페이지 (`/`, `/legacy-jobs`, `/batches`, `/insights`, `/brand-studio`, `/usage`) manual 진입 → 시각 회귀 0

### 위험 요소

- **R1**: 디자인 토큰 (색상/spacing) 표준화 욕구 발생. 완화: 본 Phase 는 변종 통합만, 토큰 시스템은 OUT-OF-SCOPE 명시
- ~~**R2**: lucide-react 미의존~~ <!-- 2026-05-06 해제: 사용자 확정 5건 #2 — lucide-react 도입 확정 (Step 2.0) -->

---

## Phase 3 — 운영 홈 row 정보밀도 정리 (4일)

목표: `PublicationActionRow.tsx` (현재 384줄, row 당 9~14 요소) 를 정보 우선순위 기반 재설계. 주요 정보 3~4개 + 추천 액션 1개 + ⋯ Dropdown 보조 액션. 4종 Badge → P2 의 `StatusBadge` 단일화.

### 변경 대상 파일

| 파일 | 변경 |
|---|---|
| `web/frontend/src/components/PublicationActionRow.tsx` | 384 → 약 180 줄 목표 재작성 |
| `web/frontend/src/components/RowDropdownMenu.tsx` | 신규 — ⋯ 메뉴 (보조 액션) |
| `web/frontend/src/components/__tests__/PublicationActionRow.test.tsx` | 신규 — 6 탭 별 row 회귀 |

### 정보 노출 정책 (확정)

| 위치 | 표시 |
|---|---|
| **항상 표시** (왼쪽→오른쪽) | 키워드 / Workflow Badge / 최신 순위 + 날짜 / Diagnosis Badge (있을 때) |
| **추천 액션 1개** (workflow_status 별) | action_required→"재발행 판단" / republishing→"진행 중" disabled / held→"해제" / active→없음 / dismissed→"복원" / draft→"URL 등록" |
| **⋯ Dropdown 메뉴** | 보류 / 제외 / 원문 열기 / 상세 보기 / 삭제(draft 만) |
| **hover 시에만** (tooltip) | URL 풀버전, held_until, held_reason, difficulty 상세, visibility status |

**삭제**: 항상 노출되던 VisibilityBadge / KeywordDifficultyBadge / 원문 링크 / "재발행 진행 중" 큰 버튼 → tooltip 또는 dropdown 으로 이전.

### 구현 단계

- [x] **Step 3.0** <!-- 2026-05-06 추가: plan-reviewer 보완 D — action_required 비율 측정 -->: 운영 DB 비율 측정은 supabase 환경 전용. **자체 결정 (보수)**: 비율을 알 수 없는 상태에서 border-l-red-500 이 100% 빨강 위험 → **lucide-react `AlertTriangle` 아이콘을 action_required row 의 키워드 좌측에 inline 표시** 채택. 색강조 대신 아이콘으로 시각 신호 분리 → 운영 데이터 누적 후 재평가
- [ ] **Step 3.1**: 추천 액션 매핑 함수 작성 (`getPrimaryAction(item: QueueItem): { label, onClick, variant } | null`). pure function 으로 분리 → 단위 테스트 가능. workflow_status 6값 + visibility_status 5값 매트릭스 정리. tests: 6 케이스 (4건)
- [ ] **Step 3.2**: `RowDropdownMenu.tsx` 신규 — P2 의 `Dialog` 또는 popover 패턴. menu items prop 으로 보류/제외/원문/상세 받음. 키보드 네비 (위/아래/Enter/ESC). tests: 열림 토글, item 클릭 콜백, ESC 닫기 (3건)
- [ ] **Step 3.3**: `PublicationActionRow.tsx` 재작성 — P2 의 `StatusBadge kind="workflow"`, `kind="diagnosis"` 호출. 4종 자체 Badge 함수 (WorkflowBadge / VisibilityBadge / DiagnosisBadge / KeywordDifficultyBadge) 제거. layout: `[키워드][workflow badge][rank·date][diagnosis?] [primary CTA] [⋯]`. action_required 시각 강조는 Step 3.0 결정 따름. 모바일 가독성은 OUT-OF-SCOPE
- [ ] **Step 3.4**: tooltip 통합 — 현재 `title=` 속성 사용. URL/held_until/difficulty 상세는 hover tooltip 만. native title 유지 (별도 tooltip 라이브러리 추가 X)
- [ ] **Step 3.5**: HoldDialog / RepublishDialog 그대로 유지 (행동은 동일, 진입 경로만 dropdown 으로 변경). tests: dropdown→Hold→Dialog 열림 (1건)
- [ ] **Step 3.6**: `__tests__/PublicationActionRow.test.tsx` 신규 — 6 탭 (action_required/republishing/held/active/dismissed/all) 별 row 렌더링 vitest. 각 탭에서 primary CTA 라벨 단언. **vitest 라벨 매칭 규칙** <!-- 2026-05-06 추가: 사용자 확정 5건 #4 -->: StatusBadge 의 라벨 텍스트 직접 매칭 금지, P6 의 `getWorkflowLabel(status)` 함수 호출 결과로 매칭 (P6 라벨 변경 시 vitest 자동 동기화). P6 미완성 시점이라도 미리 함수 호출 패턴으로 작성. 6건
- [x] **Step 3.7**: ErrorBanner.tsx 추가 <!-- 2026-05-06 추가: P2 보류분 -->: **P5 로 이연 결정** — P3 row 마이그레이션은 인라인 에러 텍스트 (`<div className="text-xs text-red-700 mt-1">`) 로 충분. ErrorBanner 는 페이지 레벨 에러 표시용 → /queue 페이지 (P5) 에서 본격 활용
- [ ] **Step 3.8**: 운영 홈 (`/`) 시각 회귀 점검 — 사용자가 manual 로 6 탭 돌면서 row 동작 확인. 정보 누락 시 dropdown 또는 tooltip 으로 복원

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] PublicationActionRow.tsx 줄 수 200 이하
- [ ] 기존 row 의 모든 액션이 primary CTA 또는 dropdown 으로 도달 가능 (회귀 0)
- [ ] 6 탭 별 vitest 통과
- [ ] vitest 라벨 매칭이 `getWorkflowLabel` 등 함수 호출 결과로 작성됨 (라벨 텍스트 직접 매칭 grep 0)
- [ ] 사용자 데모 — 6 탭 돌면서 "행동 가능, 정보 누락 0" 확인 후 다음 Phase

### 데모 시나리오 (P3 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. `/` 운영 홈 진입 → 4 큐 탭 (action_required / republishing / held / active) 별 row 시각 변화 확인
2. 1 row 클릭 → primary CTA (workflow_status 별) 라벨 정확
3. ⋯ Dropdown 클릭 → 보류 / 제외 / 원문 / 상세 / (draft 만 삭제) 메뉴 노출
4. Dropdown → Hold 클릭 → HoldDialog 열림 → 보류 사유 입력 → 저장 동작
5. action_required 시각 강조 (Step 3.0 결정에 따라 border-l-red 또는 AlertTriangle 아이콘 또는 inset shadow) 확인
6. tooltip — URL 풀버전, held_until, difficulty 상세 hover 표시
7. 모든 기존 액션 (재발행/보류/제외/복원/URL 등록) 도달 가능 회귀 0

### 위험 요소

- **R1**: dropdown 안 보조 액션 발견성 저하 → 운영자 학습 비용. 완화: dropdown trigger 옆에 hint "더 보기" microcopy. 운영 데이터 1주 후 재평가
- **R2** <!-- 2026-05-06 갱신: plan-reviewer 보완 D -->: VisibilityBadge 가 사라지면 "노출 이탈" 시각 신호 약해짐. 완화 분기 (Step 3.0 측정 결과 따름):
  - action_required 비율 ≤ 50% → row 좌측 `border-l-red-500` 색 강조 (계획안)
  - action_required 비율 > 50% → "전부 빨강" 위험. 색 강조 대신 lucide-react `AlertTriangle` 아이콘 inline 또는 우측 inset shadow 로 변경
- **R3**: difficulty badge 제거 시 "난이도 상" 키워드를 한눈에 못 봄. 완화: `/keywords` 페이지 별도 존재 + tooltip 으로 보존

---

## Phase 4 — 생성 흐름 통합 (`/create`) (4일)

목표: 신규 `/create` 페이지 — 단일 키워드 / CSV 배치 탭 통합. 기존 `NewJobForm` + `BatchUploadForm` 동일 컨테이너 안 두 탭. 고급 옵션 접기. 운영 홈 우상단 "+ 새로 만들기" 버튼 추가.

### 변경 대상 파일

| 파일 | 변경 |
|---|---|
| `web/frontend/src/app/create/page.tsx` | 신규 — 탭 컨테이너 |
| `web/frontend/src/components/CreateTabs.tsx` | 신규 — "단일 / 배치" 탭 컴포넌트 |
| `web/frontend/src/components/NewJobForm.tsx` | 고급 옵션 접기 (`<details>`) — generate_images 외 추가 옵션 |
| `web/frontend/src/components/BatchUploadForm.tsx` | 고급 옵션 접기 (cluster_dedupe / auto_publish_enabled / min_search_volume / max_difficulty) |
| `web/frontend/src/app/page.tsx` | 우상단 "+ 새로 만들기" 버튼 추가 → `/create` 이동 |
| `web/frontend/src/app/legacy-jobs/page.tsx` | 삭제 (P1 임시 보존 정리) |
| `web/frontend/src/app/batches/page.tsx` | BatchUploadForm 제거, batch list + drill-down 진입점만 유지 |
| `web/frontend/src/app/layout.tsx` | nav "생성" → `/create` 링크 |

### 구현 단계

- [ ] **Step 4.1**: `app/create/page.tsx` 신규 — `CreateTabs` 호출. URL 쿼리 `?tab=single|batch` 로 초기 탭 결정 (외부 링크 호환). 기본 `single`. 검증: `/create?tab=batch` 진입 시 배치 탭 활성
- [ ] **Step 4.2**: `CreateTabs.tsx` 신규 — P2 의 PageHeader + 탭 UI. 탭 변경 시 URL 쿼리 동기화 (`router.replace`). NewJobForm/BatchUploadForm 을 lazy import (코드 스플릿). 검증: 탭 전환 매끄럽 + URL 동기화
- [ ] **Step 4.3**: `NewJobForm.tsx` 고급 옵션 접기 — generate_images 토글은 기본 노출, 그 외 향후 추가 옵션은 `<details>` 안. 현재 옵션이 generate_images 만 있어 P4 에선 minimal 변경. 검증: form 동작 회귀 0
- [ ] **Step 4.4**: `BatchUploadForm.tsx` 고급 옵션 접기 — `min_search_volume / max_difficulty / cluster_dedupe / auto_publish_enabled` 4개를 `<details><summary>고급 옵션 (사전 필터·자동 발행)</summary>` 안에 배치. 기본 collapsed. CSV 파일 + 이름 + 처리 모드만 항상 노출. 검증: 옵션 전부 사용 회귀 0
- [ ] **Step 4.5**: `app/page.tsx` 우상단 액션 영역에 "+ 새로 만들기" 버튼 추가 (P2 의 `Button variant="primary"`). 클릭 시 `router.push("/create")`. 검증: 버튼 클릭 → /create 이동
- [ ] **Step 4.6**: `app/layout.tsx` nav "생성" 항목 → `/create`. (P1 에서 path 는 `/legacy-jobs` 였음, 본 step 에서 `/create` 로 변경)
- [ ] **Step 4.7**: `app/legacy-jobs/page.tsx` 삭제. `app/batches/page.tsx` 의 `<BatchUploadForm />` JSX 제거 (batch list + drill-down 진입만 남김). 검증: `/batches` 가 list-only 동작
- [ ] **Step 4.8** <!-- 2026-05-06 갱신: 사용자 확정 5건 #1 — `/pipeline` redirect 결정 완료 -->: `app/pipeline/page.tsx` 는 P1 Step 1.3-bis 에서 이미 `/` redirect 처리됨. P4 시점에 추가 변경 없음. 만약 P1 에서 누락됐다면 본 step 에서 redirect 어댑터 처리. 검증: `/pipeline` → `/` 진입 후 운영 홈 표시
- [ ] **Step 4.9** <!-- 2026-05-06 추가: 사용자 확정 5건 #5 — README 1줄 -->: README 임시 보존 안내 제거 — P1 Step 1.8 에서 추가한 `web/README.md` 또는 `CLAUDE.md` 변경 이력의 "P4 까지 `/legacy-jobs` 임시 보존" 문구를 P4 종료 시점에 갱신: "2026-05-XX `/legacy-jobs` 제거, `/create` 로 통합 완료". 별도 공지 X
- [ ] **Step 4.10**: vitest — `CreateTabs` 탭 전환 + URL 동기화 (3건), `BatchUploadForm` 고급 옵션 접기 (1건). 4건 추가
- [ ] **Step 4.11**: 회귀 — 단일 작업 1회 + 배치 CSV 업로드 1회 + `/jobs/[id]` 진입 정상 동작 manual 확인

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] `/create?tab=single` / `/create?tab=batch` 양쪽 동작
- [ ] `/legacy-jobs` 404 (삭제됨)
- [ ] `/batches` 에서 BatchUploadForm 사라짐 (list 만)
- [ ] `/pipeline` → `/` redirect 유지 (P1 동작 회귀 0)
- [ ] 사용자 데모 — 단일/배치 모두 새 흐름으로 1회 제출 성공

### 데모 시나리오 (P4 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. `/` 운영 홈 우상단 "+ 새로 만들기" 버튼 클릭 → `/create` 이동
2. `/create` 진입 → 단일 / 배치 탭 표시. 기본 단일 탭 활성
3. 배치 탭 클릭 → URL `?tab=batch` 동기화 + BatchUploadForm 표시
4. BatchUploadForm 의 고급 옵션 collapsed (기본). `<details>` 펼치면 cluster_dedupe / auto_publish_enabled / min_search_volume / max_difficulty 4개 노출
5. 단일 탭 → NewJobForm 으로 키워드 1개 제출 → `/jobs/[id]` 정상 진입
6. 배치 탭 → CSV 업로드 → `/batches/[id]` 정상 진입
7. `/legacy-jobs` URL 입력 → 404 확인
8. `/batches` 진입 → BatchUploadForm 없음, list + drill-down 만

### 위험 요소

- **R1**: 기존 운영자 북마크가 `/` 의 NewJobForm 을 가리킴. 완화: P1 에서 `/legacy-jobs` 보존 + P4 에서 `/` → "+ 새로 만들기" 로 명시적 entry. README 1줄 안내 (Step 4.9)
- ~~**R2**: `/pipeline` 이 nav 외에 다른 진입점이 있을 가능성~~ <!-- 2026-05-06 해제: P1 Step 1.3-bis 에서 redirect 처리 완료 -->
- **R3**: BatchUploadForm 고급 옵션 접기 후 cluster_dedupe 발견성 저하. 완화: details summary 라벨에 "고급 옵션 (사전 필터·자동 발행)" 명시

---

## Phase 5 — 검수·발행 큐 통합 (`/queue`) (6일) — 최대 작업

목표: 신규 `/queue` 페이지 — 단일 큐 (출처 무관 batch/single 모두 노출). drill-down 은 `/batches/[id]` 유지. PublicationForm/ExternalUrlForm/PublicationEditDialog 3종 → 단일 컴포넌트.

### 변경 대상 파일

| 파일 | 변경 |
|---|---|
| `web/frontend/src/app/queue/page.tsx` | 신규 — 통합 큐 |
| `web/frontend/src/components/QueueTable.tsx` | 신규 — DataTableShell 사용, 출처/상태/키워드/액션 컬럼 |
| `web/frontend/src/components/QueueItemDrawer.tsx` | 신규 — 본문 미리보기 drawer (slide-in) |
| `web/frontend/src/components/PublicationForm.tsx` | `variant=create\|edit` 통합 |
| `web/frontend/src/components/ExternalUrlForm.tsx` | 삭제 (PublicationForm variant=create 흡수) |
| `web/frontend/src/components/PublicationEditDialog.tsx` | 삭제 (PublicationForm variant=edit 흡수) |
| `web/frontend/src/app/results/[slug]/page.tsx` | redirect → `/queue?slug=...&drawer=preview` |
| `web/frontend/src/app/batches/[id]/review/page.tsx` | redirect → `/queue?source=batch&batch_id=[id]` |
| `web/frontend/src/app/batches/[id]/publish/page.tsx` | redirect → `/queue?source=batch&batch_id=[id]&status=ready_to_publish` |
| `web/frontend/src/app/batches/[id]/page.tsx` | drill-down 유지 (배치 상세 + 해당 배치만 필터링한 큐 링크) |
| `web/frontend/src/app/layout.tsx` | nav "검수·발행" → `/queue` 링크 |

### 큐 데이터 소스 (백엔드 무변경 전제) <!-- 2026-05-06 갱신: 사용자 확정 5건 #3 — frontend merge 확정 -->

기존 API 조합으로 큐 구성. **frontend merge 확정** (백엔드 use case 신설 안 함):

- **단일 출처** (jobs API): `listJobs()` → status=succeeded 인 single job 의 generated_contents
- **배치 출처** (batch API): `listBatches()` 의 모든 batch 의 review queue (`/batches/{id}/review` 기존 엔드포인트)

→ Frontend `lib/api.ts` 에 `getUnifiedQueue(filters)` 신설 — 두 API 병합 + client side merge. 백엔드 라우터 무변경.

**근거**: 운영 데이터 = 활성 batch 최대 10개 × 배치당 키워드 100 미만 = 최대 1000 row. frontend merge 가능 한도. `application/unified_queue.py` 같은 신규 use case 추가 안 함.

~~대안: 백엔드 `application/unified_queue.py` 신설~~ <!-- 2026-05-06 해제: 사용자 확정 5건 #3 -->

### 구현 단계

- [ ] **Step 5.0** <!-- 2026-05-06 추가: plan-reviewer 보완 E — ResultViewer 직렬화 경계 확인 -->: `web/frontend/src/components/ResultViewer.tsx` 의 server vs client component 확인. 첫 줄 `"use client"` 유무, 사용 hooks (useState/useEffect) 유무. 결과를 본 plan 안에 기록. drawer 재사용 시:
  - client component → drawer 안 직접 import + lazy load
  - server component → next/dynamic 으로 동적 import (`ssr: true`) + Skeleton fallback
- [ ] **Step 5.1** <!-- 2026-05-06 갱신: frontend merge 확정 -->: ~~데이터 소스 결정~~ — frontend merge 확정 (사용자 결정 #3). 본 step 은 운영 규모 점검만: 활성 batch 수 + 평균 review queue size 1회 측정해서 N+1 수용 가능 재확인. 운영 데이터 결과 (예: batch 8개, 평균 30 row) 를 plan 에 기록
- [ ] **Step 5.2**: `lib/api.ts` 에 `getUnifiedQueue(filters: { source?, status?, batch_id?, search? })` 추가. 내부적으로 `listJobs` + `listBatches.flatMap(getBatchReview)` 병합. 캐싱은 단순 5초 stale (P0)
- [ ] **Step 5.3**: `Skeleton.tsx` 추가 <!-- 2026-05-06 추가: P2 보류분 도입 -->: P2 에서 보류한 `components/ui/Skeleton.tsx` 신규 (테이블 행 / 카드 / 문단 변형). DataTableShell 의 loading slot 도 inline div → Skeleton 으로 교체. tests 2건
- [ ] **Step 5.4**: `app/queue/page.tsx` + `QueueTable.tsx` 신규 — P2 의 `DataTableShell` 사용. 컬럼: 키워드 / 출처 / 상태 (P2 StatusBadge kind="batch" or "workflow") / 다음 액션 / ⋯ 메뉴. 필터: 출처 (all/batch/single) / 상태 (multi-select) / 검색
- [ ] **Step 5.5**: `QueueItemDrawer.tsx` 신규 — slide-in drawer. 진입: row 클릭 또는 "본문 미리보기" 액션. 컨텐츠는 Step 5.0 결정에 따라 ResultViewer 재사용 (client → 직접 import, server → next/dynamic). 닫기: ESC + 외부 클릭. 검증: drawer 안 HTML 미리보기 정상
- [ ] **Step 5.6**: `PublicationForm.tsx` 통합 — `variant: "create" | "edit"`, `defaultValues?` prop. variant=create 시 ExternalUrlForm 동등, variant=edit 시 PublicationEditDialog 동등. 두 기존 컴포넌트의 props/onSubmit 시그니처 차이 흡수. tests: variant 별 렌더링 + submit 콜백 (4건)
- [ ] **Step 5.7**: `ExternalUrlForm.tsx` / `PublicationEditDialog.tsx` 삭제. 호출자 (`app/page.tsx`, `app/rankings/[id]/page.tsx`, `BulkRegisterDialog.tsx` 등) 를 `PublicationForm` 으로 sweep. grep 으로 import 전수 조사 후 일괄 교체
- [ ] **Step 5.8**: `app/batches/[id]/page.tsx` 수정 — drill-down 유지 (배치 진행 카드 + BatchProgressTable). 하단에 "이 배치의 검수 큐만 보기 → /queue?batch_id={id}" 링크 추가
- [ ] **Step 5.9**: redirect 어댑터 3개:
  - `app/results/[slug]/page.tsx` → `/queue?slug={slug}&drawer=preview`
  - `app/batches/[id]/review/page.tsx` → `/queue?source=batch&batch_id={id}&status=needs_review,ready_to_publish`
  - `app/batches/[id]/publish/page.tsx` → `/queue?source=batch&batch_id={id}&status=ready_to_publish`
  Next.js 16 redirect 사용. 검증: 외부 북마크 깨짐 0
- [ ] **Step 5.10**: 큐 액션 — row 클릭 메뉴: approve / needs_fix / reject (기존 BatchReviewQueue 동작) / URL 등록 (PublicationForm variant=create) / 본문 미리보기 / 의료법 위반 상세. 권한별 표시 분기는 OUT-OF-SCOPE (현재 운영자 단일 권한)
- [ ] **Step 5.11**: vitest — QueueTable 필터/정렬, QueueItemDrawer 열림/닫힘, PublicationForm variant 분기, redirect 어댑터 3개 (총 10건)
- [ ] **Step 5.12**: 회귀 manual — 단일 출처 1건 + 배치 출처 1건 모두 큐에 노출, URL 등록 → `ranking_orchestrator.register_publication` 호출, approve/needs_fix dropdown 동작, drawer 본문 정상

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] `/queue` 진입 시 단일+배치 모두 표시
- [ ] 출처 필터 (all/batch/single) 동작
- [ ] PublicationForm 단일 컴포넌트로 등록/수정 양쪽 동작 (3개 → 1개 통합)
- [ ] redirect 3개 동작 (외부 북마크 깨짐 0)
- [ ] needs_review item 폐기 X 정책 유지 (UI 에서 reject 가 default 액션이 아님 확인)
- [ ] 백엔드 use case 신설 0 (frontend merge 확정 — `grep -r "unified_queue" application/` 결과 0건)
- [ ] 사용자 데모 — 단일/배치 큐 통합, 발행 흐름 1회 완주

### 데모 시나리오 (P5 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. `/queue` 진입 → 단일+배치 출처 모두 row 노출 (출처 컬럼으로 구분)
2. 출처 필터 (all/batch/single) 클릭 → 큐 즉시 필터링
3. 상태 multi-select (needs_review / ready_to_publish / draft) → 큐 필터링
4. 키워드 검색창 → row 즉시 필터링
5. row 클릭 → QueueItemDrawer 열림 → ResultViewer 본문 미리보기 (Skeleton 로딩 후 컨텐츠)
6. drawer 안 "URL 등록" 클릭 → PublicationForm variant=create 표시 → URL 입력 → 저장 → ranking_orchestrator.register_publication 호출
7. 큐 row dropdown → approve / needs_fix / 본문 미리보기 / 의료법 위반 상세 정상 동작
8. `/results/{slug}` URL 입력 → `/queue?slug=...&drawer=preview` redirect
9. `/batches/{id}/review` URL 입력 → `/queue?source=batch&batch_id=...&status=...` redirect
10. `/batches/{id}` drill-down → "이 배치의 검수 큐만 보기" 링크 → `/queue?batch_id={id}` 진입

### 위험 요소

- ~~**R1**: 큐 데이터 fetch N+1~~ <!-- 2026-05-06 해제: 사용자 확정 5건 #3 — frontend merge 확정. 운영 규모 1000 row 미만으로 수용 가능 -->
- **R2**: PublicationForm variant 통합 시 두 form 의 validation 차이 흡수 누락. 완화: 두 기존 form 의 zod schema 또는 validation 코드를 P5 시작 전 diff 비교 + 통합 테스트 우선
- **R3**: `/results/[slug]` 외부 북마크가 SEO 채널에 외부 게시되어 있을 가능성. 완화: redirect 어댑터 영구 유지 (삭제 안 함)
- **R4** <!-- 2026-05-06 갱신: plan-reviewer 보완 E -->: drawer 안 ResultViewer 가 무거운 HTML 을 client 에서 lazy load 시 깜빡임. 완화 분기 (Step 5.0 결정 따름):
  - ResultViewer = client component → 직접 import + Skeleton fallback
  - ResultViewer = server component → next/dynamic ssr=true + Skeleton fallback
- **R5**: needs_review 자동 폐기 방지 — UI 에서 reject 가 dropdown 보조 액션으로만 노출 + approve/needs_fix 가 primary. 운영 철학 위반 차단

---

## Phase 6 — 카피 정리 + 라벨 매핑 단일화 (2일)

목표: `web/frontend/src/lib/labels.ts` 신규. DB enum → UI 라벨 매핑 함수 단일 출처. 모든 컴포넌트가 `getWorkflowLabel(status)` 호출. 페이지 상단 설명 문구 다이어트.

### 변경 대상 파일

| 파일 | 변경 |
|---|---|
| `web/frontend/src/lib/labels.ts` | 신규 — 매핑 함수 + 매트릭스 |
| `web/frontend/src/lib/__tests__/labels.test.ts` | 신규 — 매핑 회귀 |
| `web/frontend/src/components/ui/StatusBadge.tsx` | labels.ts import (P2 단계는 internal map, P6 에서 sweep) |
| `web/frontend/src/components/PublicationActionRow.tsx` | REASON_LABELS / VIS_LABELS 제거 → labels.ts |
| `web/frontend/src/components/BatchProgressTable.tsx` | status 라벨 sweep |
| `web/frontend/src/components/BatchReviewQueue.tsx` | status 라벨 sweep |
| 운영 홈 / 큐 / 배치 페이지 | 페이지 상단 설명 문구 압축 (1~2 문장) |

### 라벨 매핑 매트릭스 (확정 — 본 plan 의 핵심 산출물)

#### workflow_status (Publication)

| enum | UI 라벨 |
|---|---|
| `action_required` | 재발행 판단 필요 |
| `republishing` | 재발행 중 |
| `held` | 임시 보류 |
| `active` | 노출 중 |
| `dismissed` | 추적 제외 |
| `draft` | URL 등록 필요 |

#### visibility_status

| enum | UI 라벨 |
|---|---|
| `not_measured` | 미측정 |
| `exposed` | 노출 |
| `off_radar` | 노출 이탈 |
| `recovered` | 회복 |
| `persistent_off` | 장기 미노출 |

#### batch_item_status

| enum | UI 라벨 |
|---|---|
| `queued` | 대기 |
| `running` | 진행 중 |
| `succeeded` | 생성 완료 |
| `ready_to_publish` | 발행 대기 |
| `needs_review` | 검수 대기 |
| `rejected` | 검수 거부 |
| `skipped` | 건너뜀 |
| `failed` | 실패 |

#### diagnosis reason

| enum | UI 라벨 |
|---|---|
| `no_publication` | 발행 URL 미등록 |
| `no_measurement` | 측정 누락 |
| `never_indexed` | 미노출 |
| `lost_visibility` | 노출 이탈 |
| `cannibalization` | 카니발라이제이션 |

#### compliance

| 조건 | UI 라벨 |
|---|---|
| `compliance_passed=False` | 의료법 위반 발견 |
| `compliance_passed=True` | 의료법 통과 |
| `compliance_passed=null` | 미검증 |

#### difficulty grade

| enum | UI 라벨 |
|---|---|
| `missing` | 노출 불가 |
| `high` | 난이도 상 |
| `medium` | 난이도 중 |
| `low` | 난이도 하 |

### 구현 단계

- [ ] **Step 6.1**: `lib/labels.ts` 작성 — 6개 매핑 함수: `getWorkflowLabel / getVisibilityLabel / getBatchItemLabel / getDiagnosisLabel / getComplianceLabel / getDifficultyLabel`. 각 함수는 `(status: string) => string`. 미존재 enum 입력 시 raw 반환 + console.warn (개발 가시성)
- [ ] **Step 6.2**: `__tests__/labels.test.ts` — 6 매핑 × 평균 3 케이스 = 18건 vitest. 미존재 입력 fallback 단언
- [ ] **Step 6.3**: `components/ui/StatusBadge.tsx` 의 internal map 제거 → labels.ts 호출. P2 에서 작성한 색상 매트릭스는 유지 (라벨만 위임)
- [ ] **Step 6.4**: `PublicationActionRow.tsx` 의 `REASON_LABELS / VIS_LABELS` 상수 삭제 → labels.ts 호출. P3 변경과 충돌 가능 — Step 6.4 시작 전 P3 결과 diff 확인
- [ ] **Step 6.5**: `BatchProgressTable.tsx` / `BatchReviewQueue.tsx` 의 status 표시 sweep
- [ ] **Step 6.6**: grep `'대기'\|'진행 중'\|'완료'\|'실패'` 등으로 하드코딩 라벨 전수 조사 후 sweep
- [ ] **Step 6.7**: 페이지 상단 설명 문구 다이어트:
  - `app/page.tsx` (운영 홈) — 헤더 미니멀화. `/`의 h1 만 "운영 홈" 유지, 부제 제거
  - `app/queue/page.tsx` — "검수·발행 큐" 한 줄. 사용 안내는 `?` 아이콘 tooltip
  - `app/create/page.tsx` — 탭 라벨 외 설명 문구 0
  - `app/batches/[id]/page.tsx` — 배치 메타 1줄 (이름 / created_at / 상태) + 진행 카드 바로
- [ ] **Step 6.8**: 회귀 manual — 6 페이지 돌면서 라벨 일치 확인 + 영문 enum 노출 0
- [ ] **Step 6.9**: vitest 회귀 — `getWorkflowLabel` 등 호출하는 컴포넌트 테스트가 라벨 변경 후 깨지면 expectation 일괄 갱신

### 검증 게이트

- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] `lib/labels.ts` 18 vitest 통과
- [ ] grep 으로 영문 enum 직접 표시 0 (`workflow_status === "active" ? "active" : ...` 패턴 제거)
- [ ] DB 마이그레이션 0 (Supabase 변경 X)
- [ ] 기존 18 vitest 회귀 0 — <!-- 2026-05-06 추가: 사용자 확정 5건 #4 --> 현재 18 vitest 텍스트 매칭은 라벨 매핑과 무관 (BrandRegisterDialog 형식위반/slug중복, CardPlanCard 브랜드 카드 상태, ComplianceRiskBadge 의료법 메시지). P6 라벨 매핑 도입으로 깨질 vitest 0건 확인됨
- [ ] P3 에서 추가한 `__tests__/PublicationActionRow.test.tsx` 가 `getWorkflowLabel` 함수 호출 결과로 매칭 (라벨 텍스트 직접 매칭 grep 0)
- [ ] 사용자 데모 — 모든 라벨 한국어 통일, 설명 문구 정돈, "운영자가 매일 봐도 소음 없음" 확인

### 데모 시나리오 (P6 종료 시) <!-- 2026-05-06 추가: plan-reviewer 보완 C -->

1. P6 시작 전 스크린샷 1장 (운영 홈 / 큐 / 배치 / 브랜드 4 페이지) 캡처
2. P6 완료 후 동일 4 페이지 스크린샷 비교 → 영문 enum 0, 한국어 라벨 통일 확인
3. workflow_status 6종 (action_required / republishing / held / active / dismissed / draft) 모두 한국어 라벨 표시
4. visibility_status 5종 (not_measured / exposed / off_radar / recovered / persistent_off) 한국어 라벨
5. batch_item_status 8종 (queued / running / succeeded / ready_to_publish / needs_review / rejected / skipped / failed) 한국어 라벨
6. compliance / diagnosis / difficulty 한국어 라벨
7. 페이지 상단 설명 문구 다이어트 — 운영 홈 / 큐 / 생성 / 배치 상세 모두 1~2 문장 이하
8. `/_dev/ui` 의 StatusBadge sample → labels.ts 호출 결과로 라벨 자동 동기화 확인

### 위험 요소

- **R1**: enum 추가 (예: 향후 `archived`) 시 fallback 동작 검증 필요. 완화: `getWorkflowLabel` 의 fallback 케이스 vitest 1건 강제
- **R2**: 한국어 라벨 길이가 길어 row 가 줄바꿈. 완화: P2 의 StatusBadge 가 `truncate max-w-[120px]` + tooltip
- **R3**: 배치 status `ready_to_publish` 라벨 "발행 대기" 와 publication workflow `draft` 라벨 "URL 등록 필요" 간 의미 충돌 — 둘 다 발행 준비. 완화: 배치 도메인은 "발행 대기" (운영자가 URL 검증 + 발행 액션), publication 도메인은 "URL 등록 필요" (URL 자체가 미등록). 도메인 별 다른 의미라서 라벨 다른 게 정합

---

## Phase 별 검증 게이트 요약 (반드시 통과해야 다음 진행)

각 Phase 종료 시 **모두** 통과해야 다음 Phase 진입:

- [ ] `bash .claude/hooks/build-check.sh` 그린 (pyright + ruff + pytest 1296 + vitest)
- [ ] 기존 1296 pytest 회귀 0
- [ ] 기존 18 vitest + 추가 vitest 모두 통과
- [ ] 단일 흐름 시그니처 변경 0 (orchestrator.py / operations_home.py 시그니처 grep diff 확인)
- [ ] DB enum 변경 0 (config/schema.sql diff 0)
- [ ] 사용자 데모 보고 + "Phase N 완료, Phase N+1 진입 OK" 명시 승인

---

## 본 plan 에서 명시적으로 제외 (OUT-OF-SCOPE)

- **모바일 반응형** — 별도 PR. 본 plan 은 desktop 1440 기준
- **디자인 토큰 시스템** (색상/폰트 토큰화) — Phase 2 는 컴포넌트 변종 통합만, 토큰 추출 별도 PR
- **온보딩/툴팁 시스템** — 현재 native title 만 사용, 별도 라이브러리 도입 X
- **단일 흐름 백엔드 시그니처 변경** — 절대 금지 (CLAUDE.md @ project_seo_operating_philosophy.md)
- **DB enum 마이그레이션** — UI 라벨 매핑만으로 한국어화. enum 변경은 별도 운영 결정 후 별도 PR
- **권한 시스템** (관리자/운영자 분리) — 현재 단일 권한, 별도 PR
- **A/B 테스트 인프라** — UX 개선 효과 측정 별도 PR
- **다국어 (i18n)** — 한국어 단일. 향후 도입 시 labels.ts 가 i18n key 로 전환 가능하게 설계
- **Real-time push** (WebSocket) — 현재 polling 5초 그대로. WebSocketProgressReporter 도입 별도 PR
- **needs_review 자동 폐기** — 운영 철학 위반 (후보 키워드 = 전부 발행). UI 에서 reject 가 primary 가 되지 않도록만 보장

---

## 위험 요소 / 결정 필요 사항 <!-- 2026-05-06 갱신: 사용자 확정 5건 + plan-reviewer 보완 5건 반영 -->

### ✅ 사용자 확정 결정 (5건, P1 즉시 시작 가능)

1. ✅ **(P1) `/pipeline` 처리**: `/` 로 redirect 확정. Step 1.3-bis 추가. 사용자 의도 (단계별 흐름 시각화) 는 운영 홈 안 별도 섹션 또는 P5 의 `/queue` MetricStrip 으로 흡수. nav "생성" 항목은 `/create` (P4 신설) 만 가리킴
2. ✅ **(P2) lucide-react 도입**: 확정. Step 2.0 추가 (`pnpm add lucide-react` + `pnpm-lock.yaml` 커밋)
3. ✅ **(P5) Unified queue 데이터 소스**: frontend merge 확정 (운영 규모 1000 row 미만). `application/unified_queue.py` 신설 안 함
4. ✅ **(P3·P6) vitest 라벨 매칭**: 현재 18 vitest 영향 0건 (BrandRegisterDialog/CardPlanCard/ComplianceRiskBadge 모두 라벨 매핑 무관). P3 부터 신규 vitest 는 `getWorkflowLabel(status)` 함수 호출 결과로 매칭 (P6 라벨 변경 시 자동 동기화)
5. ✅ **(P1·P4) 공지 정책**: 별도 in-app 배너 X. `web/README.md` 또는 `CLAUDE.md` 변경 이력 1줄 추가 (P1 Step 1.8 + P4 Step 4.9)

### 잔존 결정 필요 사항 (Phase 시작 시점에 자체 결정)

각 Phase 시작 전 1회 자체 점검 — 사용자 결정 미루지 않음:

- **(P1 Step 1.3 시작 전) Next.js 16 redirect API**: server component 의 `redirect()` stable 여부. `node_modules/next/dist/docs/` 1회 확인. **default**: stable, server component 로 작성
- **(P2 Step 2.2 시작 전) Dialog 기반 기술**: HTML `<dialog>` vs React portal. **default**: HTML `<dialog>` (Chrome/Safari/FF 모두 stable, ESC + body scroll lock 내장)
- **(P3 Step 3.0) action_required 비율 측정**: supabase query 1회 (`SELECT workflow_status, COUNT(*) FROM publications GROUP BY workflow_status`). 결과를 plan 안 R2 완화 분기 결정 (50% 임계). **default**: 50% 이하면 border-l-red-500 / 초과면 AlertTriangle 또는 inset shadow
- **(P5 Step 5.0) ResultViewer 직렬화 경계**: `web/frontend/src/components/ResultViewer.tsx` 의 `"use client"` 유무 + hooks 사용 확인. **default**: client component 면 직접 import, server component 면 next/dynamic ssr=true + Skeleton fallback
- **(P3 R1) PublicationActionRow 보조 액션 발견성**: dropdown 학습 비용 — 1주 후 운영 데이터 재평가. P3 종료 시 즉시 결정 X (운영 사용 후 미세조정)
- **(P6 R1) 향후 enum 추가 (`archived` 등)**: fallback 동작 vitest 1건 강제 (Step 6.1 에 명시됨). 별도 사용자 결정 X
- **(공통) 데모 환경**: 실 운영 publication 240여건 그대로 사용 (default). 테스트 fixture 분리 OUT-OF-SCOPE

---

# UX Refactor 후속 — Polish Pack (4 Phase, 13.5~18.5일)

> 2026-05-06 착수. UX Refactor 6 Phase (8774267 commit, P1~P6 완료) 의 OUT-OF-SCOPE 4 항목 진행.
> 사용자 확정 결정: 디자인 토큰 + 모바일 반응형 (운영자=데스크톱 / 외부 공유=모바일) + 온보딩 + 부분 매치 키워드. **kiwipiepy 도입** (KoNLPy 폐기, JVM 의존 제거).
> Polish 의 의미 = "UX Refactor 의 시각·체감 품질을 영구화 + 신규 사용자 진입로 + backend 정확도 보강". 신규 기능 X, 기존 흐름 보강.
>
> **2026-05-06 갱신 이력**:
> - Phase 2 모바일 우선순위 사용자 확정 (A 채택: HIGH/MEDIUM/LOW 매트릭스)
> - Phase 4 의존 KoNLPy → kiwipiepy 일괄 치환 (JVM 의존 제거, cold start 0.1초)
> - plan-reviewer 보강 8건 반영 (P1 contract 명시 + sweep 사전 list, P2 jsdom matchMedia, P3 localStorage grep + 카피 표, P4 환경 검증 + 임계 분모 + env 토글)
> - P4 ETA 2~3일 → 1.5~2.5일 단축 (kiwipiepy 채택)

## 🔴 핵심 보호 원칙 (모든 Phase 공통)

1. **단일 흐름 시그니처 무변경** — `run_pipeline / run_analyze_only / run_generate_only` 인자·반환 타입 유지
2. **운영 OS 백엔드 무변경** — `application/operations_home.py`, `web/api/routers/operations_home.py` 그대로
3. **DB enum 무변경** — `workflow_status`, `visibility_state`, `batch_item_status` 등 모든 enum freeze
4. **UX Refactor 6 Phase 결과 회귀 0** — 1296 pytest + 112 vitest 모두 그린 유지 (각 Phase 종료 시 측정)
5. **Tailwind 4 의 정확한 token 시스템 API 는 추측 X** — `node_modules/tailwindcss/dist/docs/` (없으면 `dist/lib.d.mts` + `default-theme.d.mts` + `@import "tailwindcss"` 동작 방식) 1회 확인 후 결정
6. **각 Phase 별 commit + push + 데모** — UX Refactor 와 동일 패턴 (Step N.X 종료 시 build-check 그린 + 사용자에게 화면 보여주기)
7. **Phase 간 의존**: P1 → P2 → P3 (frontend 수직). P4 는 backend 독립, 어느 시점에서나 병행 가능 (default: P3 끝나고 P4)

## Phase 1 — 디자인 토큰 (4~5일, frontend 시스템)

### 목표

UX Refactor P1~P6 에서 산발적으로 적용한 색상/spacing/typography 변종을 토큰 시스템으로 영구화. StatusBadge 의 6 kind × N status 색상 매트릭스 (Tailwind 클래스 직접) → 의미 토큰 참조로 sweep.

### 변경 대상 파일

- `web/frontend/src/app/globals.css` — 기존 `@theme inline` 블록 확장 (현재 `--color-background`, `--color-foreground`, `--font-sans`, `--font-mono` 만)
- `web/frontend/src/lib/tokens.ts` — **신규**. 의미 색상 → Tailwind 클래스 매핑 함수 + StatusKind/Status 매트릭스
- `web/frontend/src/components/ui/StatusBadge.tsx` — `COLOR_MAP` 인라인 매트릭스 → `tokens.ts` 참조로 교체
- `web/frontend/src/lib/__tests__/tokens.test.ts` — **신규**. 매핑 함수 + sweep 회귀

### 의미 색상 매핑 (확정)

| 의미 토큰 | Tailwind 매핑 | 사용처 |
|---|---|---|
| `--color-status-action-required` | `red-100/red-800/red-300` | workflow.action_required, batch.failed, compliance.failed |
| `--color-status-active` | `emerald-100/emerald-800/emerald-300` | workflow.active, batch.succeeded |
| `--color-status-attention` | `amber-100/amber-800/amber-300` | workflow.republishing, compliance.warning, batch.needs_review |
| `--color-status-ready` | `green-100/green-800/green-300` | batch.ready_to_publish |
| `--color-status-pending` | `blue-100/blue-800/blue-300` | batch.running, workflow.draft |
| `--color-status-neutral` | `gray-100/gray-700/gray-300` | workflow.held, batch.queued, fallback |
| `--color-status-dismissed` | `slate-100/slate-700/slate-300` | workflow.dismissed, visibility.persistent_off, diagnosis.no_publication |
| `--color-state-error` | `red-50/red-800/red-200` | 에러 surface (border + bg + text) |
| `--color-state-warning` | `amber-50/amber-700/amber-200` | warning surface |
| `--color-state-success` | `emerald-50/emerald-700/emerald-200` | 약한 success surface (visibility.exposed, compliance.passed) |
| `--color-state-info` | `blue-50/blue-700/blue-200` | info surface (visibility.recovered) |
| `--color-state-danger-soft` | `rose-50/rose-700/rose-200` | 약한 danger (visibility.off_radar, diagnosis.never_indexed) |
| `--color-surface-base` | 기존 `--background` 재사용 | 페이지 배경 |
| `--color-surface-raised` | `white` | Card / Drawer 등 raised |
| `--color-text-primary` | 기존 `--foreground` 재사용 | 본문 |
| `--color-text-secondary` | `gray-600` | 보조 텍스트 |
| `--color-text-muted` | `gray-500` | 메타 텍스트 (timestamp 등) |

> spacing/typography 는 default Tailwind scale 활용. theme extension 만 (sm/md/lg 토큰 신규 정의 X).
> difficulty (S/A/B/C/D) 는 색상 의미가 분리되어 있어 별도 grade 토큰 (`--color-grade-s` ~ `--color-grade-d`) 5개 신규.
> diagnosis 의 `cannibalization` (fuchsia) 은 의미 충돌 가능성 — `--color-status-conflict` 1건 신규.

### 구현 단계 — ✅ 완료 (UX Refactor P1~P6 commit `8774267`, 2026-05-06)

- [x] **Step 1.0 — Tailwind 4 token API 확인** ✅ 결정: ② JS 매핑 (`tokens.ts`) 병행 채택. Tailwind class scanner 가 동적 변수를 못 잡으므로 정적 className 매핑 필요
- [x] **Step 1.0.5 — sweep 대상 사전 list** ✅ 1.5 결정으로 흡수 (287 위치 / 50+ 파일 grep 측정)
- [x] **Step 1.1 — globals.css 의 `@theme inline` 블록 확장** ✅ `--color-status-*`/`--color-state-*` CSS 변수 정의 (reference 용)
- [x] **Step 1.2 — `web/frontend/src/lib/tokens.ts` 신규 작성 + StatusBadge 회귀 contract** ✅
  - export `getStatusToken(kind, status): { bg: string; text: string; border: string }` 함수
  - 내부 매트릭스: 현재 StatusBadge `COLOR_MAP` 의 모든 (kind, status) 를 의미 토큰 키로 매핑
  - export `STATUS_TOKEN_LABELS: Record<SemanticToken, string>` (디버그용)
  - 명시 fallback: 미매핑 → `status-neutral`
  - 🔴 **회귀 contract 못박기**: 기존 `StatusBadge.test.tsx` 의 line 9, 15, 20, 25 가 `bg-red-100`, `bg-rose-50`, `bg-amber-100`, `bg-gray-100` 4 클래스를 직접 매칭 — 토큰 sweep 후에도 **동일 클래스 문자열 반환 = contract**
  - vitest: `tokens.test.ts` 신규 첫 케이스로 "기존 4개 매칭 그대로 통과" 회귀 못박기
    1. `getStatusToken('workflow', 'action_required').bg === 'bg-red-100'`
    2. `getStatusToken('visibility', 'off_radar').bg === 'bg-rose-50'`
    3. `getStatusToken('workflow', 'republishing').bg === 'bg-amber-100'`
    4. `getStatusToken('workflow', 'held').bg === 'bg-gray-100'`
  - vitest: 모든 (kind, status) 조합이 fallback 이 아닌 의미 토큰으로 매핑되는지 회귀 (P6 enum 추가 시 자동 검출)
- [x] **Step 1.3 — StatusBadge sweep + contract 검증** ✅ `COLOR_MAP` 인라인 → `getStatusToken()` 위임. 4 클래스 매칭 회귀 0
- [x] **Step 1.4 — Tailwind 클래스 직접 사용 sweep** ✅ 1.5 결정으로 별도 PR 분리 (운영자 우선순위 낮음). **2026-05-08 재검토**: 70 파일 / 321 위치 (정의·테스트 34 제외 시 ~287). Tier 1 (status badge), Tier 2 (배너/dialog), Tier 3 (grade·차트·brand_card) 분류. 사용자 결정: **연기** — 미래 디자인 시스템 변경 시점에 재검토
- [x] **Step 1.5 — 미적용 컴포넌트 plan 분리 결정** (자체 결정)
  - **결과**: 287 위치 / 50+ 파일에 색상 클래스 산발 (grep 측정). StatusBadge 외 페이지/컴포넌트의 색상 의미가 다양 (브랜드 카드 / 차트 / 배너 / 툴팁 — enum 기반 매핑 어려움)
  - **결정**: 나머지 sweep 은 별도 PR 로 분리. P1 핵심 가치 (StatusBadge 토큰화 + 의미 토큰 변수 정의) 달성 — 운영자 우선순위 낮음, 후속 PR 에서 일관성 폴리시 작업 시 진행
- [x] **Step 1.6 — 빌드 게이트 + commit + 데모** ✅ commit `8774267` (UX Refactor P1~P6 일괄). build-check 그린, vitest 143/143 (재검증 2026-05-08)

### 검증 게이트

- `bash .claude/hooks/build-check.sh` 그린
- vitest 112 → 113~120 (tokens.test 추가만큼) 그린
- Storybook 또는 `_dev/ui` 페이지에서 StatusBadge 매트릭스 시각 회귀 0 (P6 데모 페이지 재사용)

### 데모 시나리오

1. `_dev/ui` 페이지에서 6 kind × N status 모든 StatusBadge 가 변경 전과 동일한 색상으로 보임
2. `tokens.ts` 의 `getStatusToken('workflow', 'action_required')` 가 빨간 매핑 반환 (콘솔 검증)
3. globals.css 의 `--color-status-action-required` 변수가 정의되어 있고 dev 도구 inspector 에서 확인 가능

### 위험 요소

- **R1**: Tailwind 4 의 `@theme inline` 변수만으로 임의 클래스 (`bg-status-action-required`) 를 인식하지 못할 가능성 → Step 1.0 에서 검증, 못 하면 `tokens.ts` 의 명시 매핑 방식으로 우회 (default)
- **R2**: tokens.ts 변경이 시각 회귀를 일으킬 가능성 → vitest 매트릭스 회귀 + `_dev/ui` 시각 비교
- **R3**: P6 의 ComplianceRiskBadge / BrandRegisterDialog 가 자체 색상 매트릭스를 가질 경우 → Step 1.4 sweep 에 포함, 누락 시 Step 1.5 에서 별도 PR 분리

---

## Phase 2 — 모바일 반응형 (5~7일, frontend sweep)

### 목표

운영자(데스크톱 only) + 외부 공유(모바일) 두 사용 패턴 분리. 외부 공유 가능한 페이지는 모바일 우선, 운영 화면은 데스크톱 우선 + 모바일 best-effort.

### 사용자 확정 가정 (2026-05-06)

> ✅ **운영자 = 데스크톱 only / 외부 공유 = 모바일** (Phase A 채택)
> Phase 2 step 들이 아래 우선순위에 따라 작업 분량 조절.

### 우선순위 (사용자 확정)

| 우선순위 | 페이지 | 사유 |
|---|---|---|
| **HIGH** (반드시 모바일 대응) | `/queue?slug=...&drawer=preview`, `/rankings/[id]` | 외부 공유 / SEO 채널 인입 가능 (publication 상세) |
| **MEDIUM** (sanity) | `/`, `/queue`, `/batches` | 운영자가 가끔 모바일 확인 시 깨지지 않을 정도 |
| **LOW** (제외 권장) | `/create`, `/brand-studio`, `/insights`, `/usage`, `/_dev/ui` | 데스크톱 전용 — 모바일 sweep OUT-OF-SCOPE |

> `/patterns/by-id/[id]` 는 운영자만 접근 (보관함). MEDIUM 으로 강등 — 외부 공유 X.

### breakpoint 정책 (확정)

- `sm: 640px` (Tailwind default) — phone landscape / small tablet 진입
- `md: 768px` (Tailwind default) — tablet portrait
- `lg: 1024px` — desktop 진입 (현재 plan 의 desktop 1440 가정 유지)
- 1440 미만은 P2 가정 = 운영자 desktop 최소

### 구현 단계 — ✅ 완료 (UX Refactor P2 commit `8774267`, 2026-05-06)

- [x] **Step 2.0 — vitest.setup.ts 의 matchMedia polyfill** ✅ `_viewportWidth` 글로벌 + `mockViewport()` helper export (jsdom 회귀 가능)
- [x] **Step 2.1 — 공통 layout 의 nav drawer** ✅ `NavBar.tsx` 의 `md:hidden` hamburger + ESC 닫기 + 라우트 변경 시 자동 닫기
- [x] **Step 2.2 — HIGH 페이지 sweep (외부 공유 우선)** ✅ `QueueItemDrawer` 의 `absolute inset-0 md:left-auto md:right-0` (모바일 full screen, 데스크톱 right-slide)
- [x] **Step 2.3 — MEDIUM 페이지 sanity (운영자 모바일 best-effort)** ✅ DataTableShell 모바일 자동 카드 변환 (lessons.md "DataTableShell 모바일 자동 변환")
- [x] **Step 2.4 — LOW 페이지 OUT-OF-SCOPE 처리** ✅ `DesktopOnlyBanner` 컴포넌트 + `/create`, `/usage`, `/brand-studio`, `/insights` 4개 페이지 mount
- [x] **Step 2.5 — Drawer / Dialog 모바일 full screen 전환** ✅ Step 2.2 와 통합 적용
- [x] **Step 2.6 — 빌드 게이트 + commit + 데모** ✅ commit `8774267`. matchMedia mock 활용 회귀 1건 (NavBar.mobile.test.tsx)

### 검증 게이트

- `bash .claude/hooks/build-check.sh` 그린
- vitest 그린 + matchMedia mock 으로 mobile/tablet/desktop 3 viewport sanity 1~2건
- 실 모바일 (iPhone Safari + Chrome Android) 또는 chrome devtools 375px / 768px 에서 HIGH 페이지 시각 검증

### 데모 시나리오

1. iPhone Safari (또는 devtools 375px) 로 `/queue?slug=test&drawer=preview` 접속 → 본문 가독 + 액션 버튼 tap
2. 같은 환경에서 `/rankings/[id]` → 메타 + Chart 1열 스크롤
3. `/queue` 데스크톱 → 모바일 전환 시 nav drawer 동작 + 테이블 → 카드 변환
4. `/create` 모바일 진입 → "데스크톱 권장" 배너 노출 (LOW OUT-OF-SCOPE 검증)

### 위험 요소

- **R1**: Tailwind 의 `sm:`/`md:` prefix sweep 양이 많아 ETA 초과 위험 → LOW 는 sweep 제외 (사용자 확정), 안내 배너만
- **R2**: jsdom 환경의 viewport 시뮬레이션 한계 → matchMedia polyfill (Step 2.0) 으로 회귀 1~2건 가능, manual 검증 병행
- **R3**: HIGH 페이지의 외부 공유 사례 자체가 적을 수 있음 → 사용자 확정 매트릭스 신뢰, P3 종료 시 referrer 분포 1회 확인 가능

---

## Phase 3 — 온보딩 / 툴팁 (3~4일, frontend 신규)

### 목표

신규 사용자 (또는 1주 이상 미사용 운영자) 의 진입 학습 비용 감소. 첫 방문 modal + 페이지별 `?` tooltip.

### 변경 대상 파일

- `web/frontend/src/components/onboarding/WelcomeModal.tsx` — **신규**. 첫 방문 modal (3 카드)
- `web/frontend/src/components/ui/HelpTooltip.tsx` — **신규**. `?` 아이콘 + tooltip
- `web/frontend/src/lib/onboarding.ts` — **신규**. `localStorage` 기반 isOnboarded() / setOnboarded()
- `web/frontend/src/app/page.tsx` (운영 홈) — WelcomeModal mount
- `web/frontend/src/app/queue/page.tsx`, `/batches/page.tsx`, `/create/page.tsx` — HelpTooltip 삽입

### 정책 (확정)

- 첫 방문 = `localStorage.getItem("onboarded") === null`. dismiss 후 영구 미노출 (`localStorage.setItem("onboarded", "true")`)
- modal 3 카드 (확정):
  1. **"단일 키워드 만들기"** → CTA: `/create?tab=single` 이동
  2. **"CSV 배치 운영"** → CTA: `/create?tab=batch` 이동
  3. **"운영 OS 보기"** → 운영 홈 안내 (modal close, 배경 강조 X — 단순 안내)
- nav 메뉴 "도움말" 항목 추가 X (사용자 결정 nav 6개 유지)
- 페이지별 HelpTooltip 위치 (확정):
  - 운영 홈 `/` — h1 옆 `?` (운영 OS 4 트랙 설명)
  - `/queue` — h1 옆 `?` (work / monitor / archive 탭 설명)
  - `/batches` — h1 옆 `?` (CSV → 배치 → 검수 큐 흐름)
  - `/create` — h1 옆 `?` (single vs batch 차이)

### 구현 단계 — ✅ 완료 (UX Refactor P3 commit `8774267`, 2026-05-06)

- [x] **Step 3.0 — `localStorage` 기반 onboarding 라이브러리** ✅ `lib/onboarding.ts` (`cc:onboarded` namespace + SSR 안전 + vitest 3건)
- [x] **Step 3.1 — WelcomeModal 컴포넌트** ✅ `components/onboarding/WelcomeModal.tsx` 3 카드 (FileText/Files/LayoutDashboard 아이콘) + Dialog wrapper. dismiss/CTA 시 `setOnboarded()` 호출
- [x] **Step 3.2 — 운영 홈에 WelcomeModal mount** ✅ `app/page.tsx:91~94` `useEffect` 로 `!isOnboarded()` 체크 → setWelcomeOpen(true)
- [x] **Step 3.3 — HelpTooltip 컴포넌트** ✅ `ui/HelpTooltip.tsx` + `HelpTooltip.test.tsx` (hover/click + aria-describedby)
- [x] **Step 3.4 — 4개 페이지 HelpTooltip 삽입 + 카피 표 단일 출처** ✅ `lib/helpMessages.ts` 단일 출처 + `/`, `/queue`, `/batches`, `/create` 4 페이지 h1 옆 `<HelpTooltip content={helpMessages.X} />`
  - 카피 단일 출처: `web/frontend/src/lib/helpMessages.ts` 신규 (labels.ts 와 같은 패턴)
  - 4 카피 (planner 작성, 사용자 검토 대상):

    | 페이지 | 카피 (1~2 문장) |
    |---|---|
    | 운영 홈 (`/`) | "오늘 처리할 작업이 4 큐 (액션 필요 / 재발행 중 / 보류 / 노출 중) 로 분류됩니다. 액션 필요 큐부터 처리하세요." |
    | 큐 (`/queue`) | "단일 작업 결과와 배치 검수 항목을 한 곳에서 처리. 출처/상태 필터로 좁힌 뒤 row 클릭으로 본문 미리보기." |
    | 배치 (`/batches`) | "CSV 업로드한 키워드 묶음의 진행 상태. 검수 큐로 들어가면 승인/수정/거부 처리." |
    | 생성 (`/create`) | "단일 키워드는 즉시 결과, CSV 배치는 검수 큐로 흐릅니다. 단일은 분석/생성/파이프라인 모드 선택 가능." |

  - 4개 페이지 h1 옆에 `<HelpTooltip content={helpMessages.home} />` 형태 삽입
  - 검증: 모든 페이지에서 `?` 아이콘 hover 시 안내 표시 + helpMessages.ts 단일 출처
- [x] **Step 3.5 — 빌드 게이트 + commit + 데모** ✅ commit `8774267`. build-check 그린 + onboarding/HelpTooltip vitest 그린

### 검증 게이트

- `bash .claude/hooks/build-check.sh` 그린
- vitest 112 + 6 (onboarding 3 + tooltip 3) = 118 그린
- 첫 방문 (브라우저 incognito) → modal 표시 → dismiss → reload 시 미표시 (manual)

### 데모 시나리오

1. incognito 창에서 `/` 접속 → WelcomeModal 표시
2. "단일 키워드 만들기" CTA 클릭 → `/create?tab=single` 이동
3. reload `/` → modal 미표시
4. 운영 홈 h1 옆 `?` hover → "운영 OS 4 트랙" 안내 tooltip
5. `localStorage.removeItem("onboarded")` → reload `/` → modal 다시 표시 (디버그용)

### 위험 요소

- **R1**: `localStorage` 가 incognito 또는 운영자 브라우저 cleanup 으로 자주 reset 될 가능성 → 의도적 허용 (UX Refactor 6 Phase 와 동일하게 진입 후 반복 학습 가능)
- **R2**: HelpTooltip 의 click vs hover 분기 — 모바일/데스크톱 분리 — Phase 2 의 모바일 정책과 정합 필요
- **R3**: WelcomeModal 의 CTA 가 라우팅 시 `setOnboarded()` 호출 후 navigate 순서 race condition → useEffect 후 router.push, vitest 로 회귀

---

## Phase 4 — 부분 매치 키워드 검증 (1.5~2.5일, backend, kiwipiepy)

### 목표

`title_validator._check_keyword_repetition` 의 키워드 반복 검증을 형태소/공백 정규화 강화. "다이어트한의원" vs "다이어트 한의원" 동일 처리.

> **2026-05-06 갱신**: KoNLPy → kiwipiepy 채택. 사유 = JVM 의존 제거 (Render 컨테이너 추가 설정 0), cold start 1~2초 → 0.1초 (10배), pip 1개로 끝, 정확도는 Mecab 수준 (KoNLPy Okt 동등 또는 우수).

### 변경 대상 파일

- `pyproject.toml` — `kiwipiepy>=0.17` 의존 추가 (`dependencies`)
- `domain/generation/title_validator.py` — `_normalize_morpheme()` helper 추가 + `_check_keyword_repetition` 호출 분기
- `tests/test_generation/test_title_validator.py` — 형태소 매칭 6 신규 케이스
- `config/settings.py` — `TITLE_VALIDATOR_MORPHEME_THRESHOLD` env 토글 (default 0.7)
- `application/stage_runner.py` (또는 호출자) — kiwipiepy import 실패 시 degrade 분기 (fallback, drop-in 안전망)

### kiwipiepy 도입 정책 (확정)

- **사용자 결정**: kiwipiepy 채택 (KoNLPy 폐기)
- 형태소 분석기: `Kiwi` (`from kiwipiepy import Kiwi`)
- 사용 패턴:
  ```python
  from kiwipiepy import Kiwi
  kiwi = Kiwi()
  result = kiwi.analyze("다이어트한의원")
  nouns = [t.form for t in result[0][0] if t.tag.startswith("NN")]
  # → ["다이어트", "한의원"]
  ```
- **fallback (필수)**: `from kiwipiepy import Kiwi` ImportError 시 → 공백 제거 + lowercase 만으로 degrade. ImportError 를 흡수하지 않고 logger.warning 1회 + 모듈 단위 캐시
- ImportError 발생 가능 환경: ARM 일부 wheel 미지원 — fallback 으로 graceful degrade (KoNLPy plan 과 동일 패턴 유지)
- **JVM 의존 제거**: Dockerfile 수정 불필요. Render 컨테이너 추가 설정 0
- 대안: kiwipiepy 가 본 프로젝트 다른 곳에서 쓰이지 않음 (확인 필요) → Step 4.0 에서 grep 1회

### 구현 단계

- [x] **Step 4.0 — kiwipiepy 의존 영향 평가 + 환경 검증 (plan-reviewer 보강 B/C)** ✅ 2026-05-08 — cold start 측정 import 0.087s + Kiwi() 0.655s + first analyze 1.130s + second 0.0002s ≈ 1.87s (Plan 추정 0.1s 보다 느리지만 singleton 캐시로 worker 당 1회만)
  - `grep -r "kiwipiepy\|konlpy\|from kiwipiepy\|from konlpy" .` 으로 본 프로젝트의 기존 사용 확인
  - **default**: 미사용 — pyproject.toml 에 의존 추가
  - 🔴 **production 환경 검증** (1회):
    - dev: `python -c "from kiwipiepy import Kiwi; Kiwi()"` 통과
    - prod (Render 시뮬레이션): linux x86_64 wheel 설치 통과 확인
    - Render 배포 영향: **0** (JVM 의존 없음 — kiwipiepy 는 wheel + C++ 바이너리만)
  - 🔴 **cold start 측정** (1회): `time python -c "from kiwipiepy import Kiwi; k = Kiwi(); k.analyze('테스트')"` 1회 측정
    - 추정 0.1초 (KoNLPy JVM 1~2초 대비 10배)
    - 결과를 plan 안에 기록 후 Step 4.2 의 모듈 단위 캐시 (singleton 패턴) 정당성 확인
  - ImportError fallback 정책: 만약 wheel 미지원 환경 (ARM 일부) → fallback 으로 graceful degrade
- [x] **Step 4.1 — pyproject.toml 의존 추가** ✅ 2026-05-08 — pyproject 에 이미 추가돼 있었으나 venv (+ system python) 양쪽 미설치였음. `pip install kiwipiepy>=0.17` 으로 양쪽 설치 (build-check.sh 가 system pytest 사용)
  - `dependencies` 에 `kiwipiepy>=0.17` 추가 (정상 흐름 필수)
  - `pip install -e ".[dev]"` 후 `from kiwipiepy import Kiwi` 동작 확인
  - 검증: `python -c "from kiwipiepy import Kiwi; k = Kiwi(); print([t.form for t in k.analyze('다이어트 한의원')[0][0] if t.tag.startswith('NN')])"` 출력 → `["다이어트", "한의원"]`
- [x] **Step 4.2 — `_normalize_morpheme(text, keyword)` helper 추가** ✅ 2026-05-08 — `domain/generation/title_validator.py:155~214` 에 이미 구현돼 있었음. singleton 캐시 (`_kiwi_instance` + `_kiwi_unavailable`) + ImportError fallback
  - title_validator.py 에 신규 함수 + 모듈 단위 Kiwi 캐시 (`_kiwi_instance: Kiwi | None = None`, lazy init via singleton)
  - 동작:
    1. text 와 keyword 양쪽에 `kiwi.analyze()` → `tag.startswith("NN")` 필터로 명사 set 추출
    2. set 교집합 비율 계산 — `TITLE_VALIDATOR_MORPHEME_THRESHOLD` (default 0.7) 이상이면 "포함" 판정
    3. fallback (ImportError): 기존 `_normalize` 만 사용 (degrade)
  - 모듈 단위 캐시 (singleton 패턴) 로 worker 당 1회만 시동 (cold start 0.1초 추정 — Step 4.0 측정 결과)
  - 검증: `_normalize_morpheme("다이어트 한의원 추천", "다이어트한의원")` → True
- [x] **Step 4.3 — `_check_keyword_repetition` 분기** ✅ 2026-05-08 (commit `05f9345`)
  - exact 1회 일 때 마스킹 후 형태소 매칭 → `keyword_repetition_morpheme` warning issue 추가 (passed=True 유지)
  - exact 0/2+ 케이스는 기존 동작 유지 (회귀 0)
  - 운영 1주 후 severity 상향 (error) 결정 — 잔존 결정 사항
- [x] **Step 4.4 — 형태소 매칭 11 신규 pytest 케이스** ✅ 2026-05-08 — `TestNormalizeMorpheme` 8건 + `TestKeywordRepetitionMorphemeBranch` 3건. 단순 helper 검증 + validate_title 분기 회귀 + kiwi 미사용 fallback. 32/32 그린
  - 🔴 **임계값 분모 명시**: 분모 = **keyword 명사 set 크기** (recall 기준 — keyword 의 명사가 title 에 얼마나 포함되었는지)
  - 임계값 0.7 은 default, env 토글 `TITLE_VALIDATOR_MORPHEME_THRESHOLD` 추가 (운영 데이터 누적 후 조정)
  - 케이스:
    1. "다이어트 한의원 추천" + "다이어트한의원" → 매칭 (keyword 명사 2개 모두 포함, ratio=1.0)
    2. "한의원 다이어트 후기" + "다이어트한의원" → 매칭 (어순 다름, ratio=1.0)
    3. "한의원 추천 다이어트" + "다이어트한의원" → 매칭 (ratio=1.0)
    4. "강남 다이어트한의원" + "다이어트 한의원" → 매칭 (역방향, ratio=1.0)
    5. **70% 경계값 케이스**: keyword 명사 3개 중 2개 포함 = 0.67 → 통과 (미매칭) / 3개 모두 = 1.0 → fail (매칭)
    6. kiwipiepy ImportError mock → fallback 만으로 동작 검증 (`_normalize` exact match 결과 검증)
  - 기존 21 vitest 회귀 0
- [x] **Step 4.5 — 빌드 게이트 + commit + 데모** ✅ 2026-05-08 (commit `05f9345`) — `build-check.sh` PASSED, vitest 143/143, pytest 1316/1316

### 검증 게이트

- `bash .claude/hooks/build-check.sh` 그린
- pytest 1296 + 6 (형태소 매칭) = 1302 그린
- kiwipiepy ImportError 시뮬레이션 (mock) 으로 fallback 동작 회귀 1건
- production wheel 설치 1회 검증 (Step 4.0)

### 데모 시나리오

1. `python -c "from domain.generation.title_validator import _normalize_morpheme; print(_normalize_morpheme('다이어트 한의원 추천', '다이어트한의원'))"` → True
2. kiwipiepy 미설치 환경 (mock) → degrade fallback (exact match 만)
3. 실제 outline 생성 시 "다이어트 한의원 추천 (강남)" 같은 title 이 "다이어트한의원" 키워드와 매칭 — 회귀 없음
4. cold start 측정: `time python -c "from kiwipiepy import Kiwi; Kiwi()"` → 0.1초대 확인

### 위험 요소

- ✅ **R1 (구 KoNLPy JVM 의존)**: kiwipiepy 채택으로 N/A — JVM 미사용
- ✅ **R2 (구 Render JVM 설정)**: kiwipiepy 채택으로 자동 해결 (Dockerfile 수정 불필요)
- ✅ **R3 (구 cold start 1~2초)**: kiwipiepy 채택으로 자동 해결 (0.1초 → worker N개 spawn 영향 없음, 모듈 단위 캐시 1회 시동)
- **R4**: 형태소 매칭의 70% 임계값이 false positive 유발 가능성 → severity=warning 으로 시작 + env 토글 (`TITLE_VALIDATOR_MORPHEME_THRESHOLD`) 로 1주 운영 후 미세 조정
- **R5**: ARM 일부 wheel 미지원 환경 → fallback 으로 graceful degrade (Step 4.0 에서 wheel 검증)
- **R6**: kiwipiepy 라이센스 — LGPL 2.1+ (KoNLPy Okt 의 Apache-2.0 보다 강함, 단 dynamic linking 으로 사용 시 통합 안전). 외부 배포 SaaS 운영에는 영향 없음 — Step 4.0 에서 1회 확인

---

## 사용자 결정 사항 (이미 답변 / 잔존)

각 Phase 시작 전 사용자 답변 또는 자체 결정:

1. ✅ **(Phase 1 Step 1.0) Tailwind 4 token API 방식**: `@theme inline` CSS 변수 only vs JS 매핑 병행 — **확정**: 병행 (자체 결정)
2. ✅ **(Phase 2 Step 2.0) 모바일 우선순위**: "운영자 = 데스크톱 only / 외부 공유 = 모바일" + HIGH/MEDIUM/LOW 매트릭스 — **확정** (2026-05-06): A 채택. HIGH = `/queue?slug=...&drawer=preview` + `/rankings/[id]` / MEDIUM = `/`, `/queue`, `/batches` (sanity) / LOW = `/create`, `/brand-studio`, `/insights`, `/usage`, `/_dev/ui` (제외)
3. ✅ **(Phase 3 Step 3.0) WelcomeModal 트리거 조건**: `localStorage` 키 — **확정**: `cc:onboarded` (namespace prefix 로 충돌 회피)
4. ✅ **(Phase 4 의존) 형태소 분석기 채택**: KoNLPy → kiwipiepy — **확정** (2026-05-06): JVM 의존 제거, cold start 10배 단축, Render 추가 설정 0
5. ✅ **(Phase 4 Step 4.0) kiwipiepy 의존 위치**: `dependencies` (정상 흐름 필수) — **확정** (정상 흐름에서 사용, optional 분리 불필요)
6. ✅ **(공통) 데모 환경**: dev 서버 + 실 운영 데이터 그대로 사용. 별도 fixture 분리 OUT-OF-SCOPE
7. ✅ **(공통) Phase 순서**: P1 → P2 → P3 → P4 (default). P4 는 backend 독립 — 어느 시점에서나 병행 가능

### 잔존 결정 사항 (운영 데이터 누적 후 결정)

- **(P3 종료 시)** 온보딩 가치 측정 메트릭: 1주 후 신규 진입 운영자 학습 시간 / modal dismiss 비율 / HelpTooltip click 횟수 측정 후 효과 평가. **현 plan 안에서는 OUT-OF-SCOPE** — 별도 P3 후속 PR 로 분리 가능
- **(P4 Step 4.3)** 형태소 매칭 severity = warning 으로 시작 → 1주 운영 후 error 상향 결정. `TITLE_VALIDATOR_MORPHEME_THRESHOLD` env 토글로 임계값 0.7 미세 조정 가능

## OUT-OF-SCOPE (영구 제외)

- **Slack notifier 연결** — Phase 4 PR1 에서 인프라만 도입, 실 운영 webhook 연결은 사용자 결정 후 별도 작업 (memory 참조)
- **rules.py 스팸 카테고리 통합** — title_validator 의 `_TITLE_SPAM_LITERALS` 와 compliance/rules.py 의 `FORBIDDEN_LITERALS` 통합은 SPEC-SEO-TEXT.md + SPEC-BRAND-CARD.md + 5 파일 동시 수정 의무 회피
- **Title 단독 LLM helper** — title 만 LLM 으로 재생성하는 helper 는 M2 톤 락 보호 (도입부 흔들림 위험) — 영구 금지
- **다국어 (i18n)** — 한국어 단일 유지 (UX Refactor OUT-OF-SCOPE 와 동일)
- **A/B 테스트 인프라** — Polish Pack 효과 측정은 별도 PR
- **Real-time push (WebSocket)** — polling 5초 유지
- **권한 시스템 (관리자/운영자 분리)** — 단일 권한 유지
- **Storybook 도입** — `_dev/ui` 페이지로 충분, 별도 도구 도입 X
- **Visual regression 테스트 (Percy / Chromatic)** — manual 검증 우선, 도구 도입 OUT-OF-SCOPE
- **모바일 native 앱** — 웹 반응형 한정

## 🆕 Blog Channels — 블로그 지정 발행 + URL 입력 (2026-05-07 신규)

### 배경

운영자가 보유한 **여러 네이버 블로그 채널** 을 시스템에 등록해 두고, 발행 시
어느 채널에 올렸는지 명시 + 그 글의 URL 입력. 발행 자체는 수동 (현재 방식
유지) — 자동 업로드 X.

### 사용자 결정 (2026-05-07)

- 블로그 모델: **여러 채널 등록 + 선택** (단순 prefix 보관 X, brand_profiles 재사용 X)
- 발행: **수동 + URL 입력만** (Selenium/네이버 API X)
- UI: **PublicationForm (단일) + CSV 업로드 컬럼 + 검수 큐 인라인 셀렉트** 모두

### 설계 골자

| 계층 | 신규 자산 |
|---|---|
| DB | `blog_channels` 테이블 + `publications.blog_channel_id` + `keyword_batch_items.blog_channel_id` |
| Domain | `domain/blog_channel/` (격리, model + storage) |
| Application | (별도 합성 함수 불필요 — orchestrator 가 channel_id 그대로 전달) |
| Web API | `web/api/routers/blog_channels.py` — CRUD |
| Frontend | `lib/api.ts` 확장 + `PublicationForm` 셀렉트 + `/blogs` 페이지 + 검수 큐 |

### Phase 1 — 백엔드 (DB + 도메인 + API) ✅ 완료 (2026-05-07, commit `763c2a1`)

- [x] `config/schema.sql` — `blog_channels` 테이블 신설
  - id (uuid), name (별칭), blog_id (네이버 ID — `myblog123`), homepage_url, memo, is_default (bool), created_at, updated_at
  - unique(name), unique(blog_id)
- [x] `config/schema.sql` — `publications` + `keyword_batch_items` 에 `blog_channel_id uuid references blog_channels(id) on delete set null` 추가
- [x] `domain/blog_channel/__init__.py` + `model.py` — `BlogChannel` Pydantic
- [x] `domain/blog_channel/storage.py` — Supabase CRUD (`list_channels`, `get_channel`, `create_channel`, `update_channel`, `delete_channel`, `find_channel_by_name`, `find_channel_by_blog_id`, `get_default_channel`)
- [x] `.claude/hooks/architecture-check.sh` — `STAGE_ORDER[blog_channel]=0` 격리 도메인 등록
- [x] `domain/ranking/model.py` — `Publication.blog_channel_id: str | None = None` 추가
- [x] `domain/ranking/storage.py` — insert/update/select 시 blog_channel_id 매핑
- [x] `domain/batch/model.py` — `KeywordBatchItem.blog_channel_id: str | None = None`
- [x] `domain/batch/storage.py` — payload 변환에 blog_channel_id 추가
- [x] `domain/batch/csv_parser.py` — `blog` 컬럼 + DI 패턴 `blog_resolver` (도메인 격리 유지)
- [x] `application/batch_orchestrator.py` — `_build_blog_resolver()` (list_channels 1회 dict 캐시)
- [x] `application/auto_publisher.py` — `register_publication` 호출 시 `blog_channel_id` 전파
- [x] `application/ranking_orchestrator.py` — `register_publication`/`update_publication`/`bulk_register_publications` 모두 blog_channel_id 인자 추가
- [x] `web/api/routers/blog_channels.py` — `GET/POST/PATCH/DELETE /blog-channels` (DELETE 는 `-> Response` 직접 반환 — `-> None` + status_code=204 충돌 회피)
- [x] `web/api/main.py` — 라우터 등록
- [x] `tests/test_blog_channel/test_model.py` (3건) + `tests/test_batch/test_csv_parser.py` blog_resolver 회귀 (2건)
- [x] `bash .claude/hooks/build-check.sh` 그린 확인 (1309 passed, 사전 morpheme fail 4건은 환경 의존성)
- [x] **Supabase 운영 DB 마이그레이션 적용 완료 (2026-05-08)**

### Phase 2 — 프론트엔드 채널 관리 + 단일 발행 UI ✅ 완료 (2026-05-07, commit `8e2f27c`)

- [x] `web/frontend/src/lib/api.ts` — `BlogChannel` 타입 + `listBlogChannels/createBlogChannel/updateBlogChannel/deleteBlogChannel` 함수 + `Publication.blog_channel_id`
- [x] `web/frontend/src/lib/swr.ts` — `K.blogChannels` 키 + `fetchOps.blogChannels` 헬퍼
- [x] `web/frontend/src/app/blogs/page.tsx` — 채널 CRUD + Dialog 폼 (별칭/blog_id/홈페이지/메모/기본 채널, blog_id 입력 시 homepage 자동 채움)
- [x] `web/frontend/src/app/blogs/loading.tsx` — Skeleton
- [x] `web/frontend/src/components/NavBar.tsx` — "관리" matches 에 `/blogs` 포함 + `/usage` 페이지 진입 링크
- [x] `web/frontend/src/components/PublicationForm.tsx` — 채널 셀렉트 + default 자동 선택 + "+ 채널 관리" 링크
- [x] `web/frontend/src/components/PublicationActionRow.tsx` — `@채널명` 배지 + tooltip 채널 정보
- [x] `web/frontend/src/lib/api.ts` — `createPublication/updatePublication` 시그니처에 `blog_channel_id` 추가
- [x] vitest: `PublicationForm.test.tsx` 채널 셀렉트 옵션·default 자동 선택·미등록 케이스 (+2건, 6/6)

### Phase 3 — 배치 CSV + 검수 큐 ✅ 완료 (2026-05-07, commit `e80941b`)

- [x] `web/frontend/src/components/BatchUploadForm.tsx` — `blog` 컬럼 안내 + `/blogs` 진입 링크
- [x] `web/frontend/src/components/BulkRegisterDialog.tsx` — "이번 등록의 블로그 채널" 일괄 셀렉트 (모든 row 같은 채널)
- [x] `web/frontend/src/components/QueueTable.tsx` — "블로그" 컬럼 추가 (별칭 + tooltip + 삭제된 채널 처리, dedupe 30초)
- [x] **운영 절차** — Drawer 의 PublicationForm 셀렉트가 인라인 매핑 처리 (별도 row 인라인 셀렉트는 OUT-OF-SCOPE)
- [x] vitest 143/143, tsc 0 error, build 성공, 백엔드 pytest 228/228

### 운영 절차

- 신규 운영자 첫 진입 시 `/blogs` 에서 최소 1개 채널 등록 권장 (이후 PublicationForm default 작동)
- 미지정 채널은 `null` 로 저장 — 기존 데이터 무손실 (마이그레이션 우려 없음)
- CSV 의 `blog` 컬럼은 채널 별칭(`name`) 또는 네이버 blog_id 둘 다 인식 (application lookup 단일 출처)

### 결정 게이트

- Phase 1 완료 후 사용자 확인 → Phase 2 착수
- Phase 2 완료 후 사용자 확인 → Phase 3 착수
- 단계별 commit + push, main 직커밋 (테스트 그린 시)

## 참조

- UX Refactor 6 Phase plan (본 todo.md 1511~ 라인)
- 8774267 commit (UX Refactor P1~P6 완료)
- `web/frontend/AGENTS.md` ("This is NOT the Next.js you know" — Next.js 16 docs 우선)
- `web/frontend/src/components/ui/StatusBadge.tsx` (Phase 1 sweep 대상)
- `web/frontend/src/app/globals.css` (Phase 1 `@theme inline` 확장)
- `domain/generation/title_validator.py` (Phase 4 대상)
- `pyproject.toml` (Phase 4 KoNLPy 의존 추가)
- `tasks/lessons.md` (실수 패턴, 매 Phase 종료 시 참조 + 갱신)
- memory: `feedback_no_emoji.md` (이모지 사용 금지), `project_seo_operating_philosophy.md` (단일 흐름 보호)

---

## 🩹 Phase J1 — Job Durability 출혈 봉합 (2026-05-08 착수, 1주)

> 2026-05-08 운영 사고 (`/api/jobs/5886b339a0a1` 폴링 502→503→404 100+회) 분석 결과, in-memory `JobManager._jobs` dict 가 컨테이너 재시작 시 휘발하는 구조가 근본 원인. Phase J1 은 **구조 변경 없이** 같은 사고가 또 나도 (1) 사용자가 인지 가능 (2) 트래픽 폭주 차단 (3) 결과 보존을 보장한다. 구조적 해결은 Phase J2.

### J1.1 frontend — 폴링 retry-bound ✅ (2026-05-08)
- [x] `web/frontend/src/lib/api.ts` 또는 폴링 hook — 404 연속 3회 또는 502/503 누적 3회 시 폴링 즉시 중단 — `ApiError` 클래스 + 신규 `lib/useJobPolling.ts` hook 으로 분리
- [x] ErrorBanner 안내 문구: "백엔드가 재시작되어 진행 상태를 분실했습니다. `output/{slug}/{ts}/` 또는 결과 보관함에서 결과를 확인하거나 재실행하세요" — `app/jobs/[id]/page.tsx` 에서 `aborted=true` 시 표시
- [ ] ~~`useJobProgress` WebSocket 도 동일 N회 reconnect 후 중단 + 동일 안내~~ — 현재 `useJobProgress` 가 reconnect 자체를 안 가지고 있어 N=1 (단발 onerror 종료) 상태. 폴링 retry-bound 가 동시 트리거하면 ErrorBanner 가 동일 안내를 한다. WS reconnect 도입 자체는 범위 밖이라 J2 또는 별도 차수로 이연
- [x] vitest — 404 3회 mock → 폴링 중단 + onError 호출 검증 — `lib/__tests__/useJobPolling.test.tsx` 5/5 (404·502 누적 / 카운터 reset / terminal 자연 종결 / 401 누적 미발동)

### J1.2 운영 env 동시성 하향 (Render Dashboard, 코드 변경 0) ✅ (2026-05-08)
- [x] `IMAGE_PARALLEL_WORKERS=2` (기본 5 → Gemini 병렬 base64 메모리 절감) — 사용자 Render Dashboard 적용
- [x] `BRIGHTDATA_CONCURRENT_LIMIT=3` (기본 5) — 사용자 Render Dashboard 적용
- [x] `BATCH_MAX_WORKERS=1` (기본 2) — 사용자 Render Dashboard 적용
- [x] `config/.env.example` 주석에 운영 권장값 기록 — Phase J1.2 헤더 + 3개 키 권장값 코멘트 추가

### J1.3 Render Service Instance 업그레이드 — Standard 미노출, Starter 유지 (2026-05-08)
- [x] **사용자 결정** — Render Dashboard 에서 Standard plan 미노출 (workspace tier 또는 region 제약으로 추정). 사용자가 Starter 로 plan 업데이트 처리. `render.yaml` 변경 0건. RAM 512MB 그대로 유지 — J1.2 env 동시성 하향과 J1.4 재시작 알림으로 메모리 피크 자체를 줄이는 방향
- [x] ~~업그레이드 후 24시간 메모리 그래프 모니터링~~ — 업그레이드 미수행이므로 J1.5 의 1주 502/404 빈도 모니터링으로 대체
- [x] ~~commit msg 에 비용 차이 명시~~ — N/A
- 후속 검토: 1주 모니터링 결과 메모리 피크가 여전히 OOM 트리거하면 (1) Standard 노출 회복 경로 (workspace upgrade) 또는 (2) Phase J2 영속화로 in-memory 의존 자체 제거 — 둘 중 비용 효율적인 쪽 선택

### J1.4 재시작 알림 (notifier 재사용) ✅ (2026-05-08)
- [x] `web/api/main.py` startup hook 에 "재시작 감지" 로직 — `RENDER_INSTANCE_ID` 또는 hostname 식별 → `notifier.send_text(":arrows_clockwise: *백엔드 재시작 감지* — instance=...")` 1회 발송. logger.info 도 동시 기록
- [x] Slack webhook 미설정 시 noop (기존 패턴 유지) — `notifier.send_text` 자체가 webhook 부재 시 즉시 return

### J1.5 검증 + commit
- [x] `bash .claude/hooks/build-check.sh` 그린 — pyright 시스템 미설치 SKIP, ruff/format 그린, useJobPolling vitest 5/5. 풀 vitest 136 passed + PublicationActionRow/PublicationForm 2 file failed 는 baseline `swr` import 사전 실패 (내 변경과 무관, stash 후 동일 재현 확인)
- [x] commit `feat(ops): Phase J1 — 폴링 retry-bound + 재시작 알림 + .env.example 권장값` — render.yaml 미변경 (사용자 인계)
- [ ] **사용자 작업** — 운영 1주 모니터링 (메모리 그래프 + 502/404 발생 빈도) → Phase J2 착수 결정

---

## 💾 Phase J2 — Job 상태 Supabase 영속화 (2026-05-08 착수, 5 PR)

> in-memory dict 를 정본에서 제거하고 **Supabase 가 단일 출처**, in-memory 는 캐시로 강등. 컨테이너 재시작 후에도 `GET /api/jobs/{id}` 가 200 OK + `status=orphaned` 같은 의미있는 종결을 반환. SPEC-BATCH 의 `domain/batch/storage.py` 와 동일한 single-source-of-truth 정신. **`application/orchestrator.run_pipeline` / `run_analyze_only` / `run_generate_only` 시그니처 무변경** (단일 흐름 보호).
>
> **rollout**: feature flag `JOB_PERSISTENCE_ENABLED` (default false) 로 PR 마다 단계 활성화. 5 PR 분할로 partial state 가 운영 안전하도록 설계 (plan-reviewer 2026-05-08 권장). PR2 후 staging 에서 flag on → DB 채워지는지 관찰 → PR3 진행.

### J2.0 feature flag 동작 분기 (전 PR 공통 약속)
- [ ] `JOB_PERSISTENCE_ENABLED=false` (default) — J2.3~J2.5 모든 신규 경로 noop, in-memory 100% fallback. PR2 이후 모든 신규 코드는 이 flag 분기 통과 후에만 DB 접근
- [ ] `JOB_PERSISTENCE_ENABLED=true` — write-through 활성. flag off → on 전환 시 누락된 in-flight job 은 다음 컨테이너 cycle 에서 orphaned 마킹 (자연 손실)
- [ ] **graceful degrade**: Supabase write/read 실패 시 `logger.warning` 흡수 + in-memory only 로 자동 강등. 본 흐름 차단 금지 (notifier 패턴 그대로)
- [ ] **fire-and-forget 정책**: `_submit` 의 `insert_job` 만 동기 (transactional 보장). status update / heartbeat / progress_event 는 모두 fire-and-forget + 실패 logger.warning. submit 응답 latency 추가 ~100ms 만 허용

### PR1 — J2.1+J2.2 schema + storage + flag 인프라 ✅ (2026-05-08, commit 469497e)
- [x] `config/schema.sql` 에 `jobs` 테이블 추가 (idempotent) + `progress_events`
- [x] index `idx_jobs_status_heartbeat`, `idx_jobs_created_at`, `idx_progress_events_created`
- [x] schema 마이그레이션 절차 — 사용자 Supabase Dashboard SQL Editor 적용 완료
- [x] `web/api/job_store.py` 신규 — 8 함수 (CRUD + 2종 orphaned 마킹)
- [x] `config/settings.py` — `job_persistence_enabled` (False) / `job_heartbeat_seconds=30` / `job_orphaned_grace_seconds=300`
- [x] `config/.env.example` 주석 — flag + grace 가이드
- [x] `tests/test_web/test_job_store.py` — 20/20 통과

### PR2 — J2.3 일부 (write-through: insert + status update 4지점) ✅ (2026-05-08, commit cc18299)
- [x] `JobManager._submit` 동기 insert_job (graceful degrade)
- [x] `_run_job` running/succeeded/failed + cancel 분기 + finally 분기 — 5지점 _persist_status
- [x] `_arm_timeout._check` timed_out _persist_status
- [x] `cancel_job` cancelled _persist_status (future.cancel 성공/실패 양쪽)
- [x] `_persist_status(job, status, error=None, started_at=None, finished_at=None, result=None)` 헬퍼 단일 진입점
- [x] `tests/test_web/test_job_manager_persistence.py` — 8/8 (flag on/off + 4지점 + graceful)
- [x] `INSTANCE_ID` 모듈 상수 (RENDER_INSTANCE_ID 또는 hostname) — PR4 sweep 사전 준비

### PR3 — J2.3 잔여 + J2.4 (heartbeat + progress_events + GET fallback) ✅ (2026-05-08, commit 09e9fec)
- [x] heartbeat daemon thread (lazy 시작 + shutdown stop event + flag 매 tick 재평가)
- [x] `JobEventBus.emit` 내부에서 append_progress_event (격리 유지 — `WebSocketProgressReporter` 무변경, seq 자동 부여)
- [x] `web/api/routers/jobs.py:get_job` — in-memory miss + flag on → DB fallback. orphaned 도 200 OK
- [x] 클라이언트 `useJobPolling.TERMINAL_STATUSES` 에 `orphaned` 추가 + `app/jobs/[id]/page.tsx` 분기 (warning ErrorBanner)
- [x] `tests/test_web/test_progress_persistence.py` 5/5 + `test_jobs_router.py` 4/4 + heartbeat 회귀 +3
- [x] `useJobPolling.test.tsx` orphaned terminal 회귀 +1

### PR4 — J2.5 startup + 5min sweep + 알림 dedupe ✅ (2026-05-08, commit 5076722)
- [x] `web/api/main.py` startup — `mark_running_as_orphaned(instance_id)` + count 회수
- [x] 5분 주기 sweep — `asyncio.create_task(_orphaned_sweep_loop)`. tick 마다 settings 재평가, Supabase 장애 graceful continue
- [x] 알림 dedupe — orphaned > 0 시 통합 메시지 (`재시작 감지 instance=X / orphaned=N`), 0 시 J1.4 형식 그대로
- [x] sweep tick count > 0 시 별도 알림 (`:mag: orphaned sweep — N job(s)`)
- [x] `config/settings.py` — `job_sweep_interval_seconds=300` 추가
- [x] shutdown 에 sweep_task.cancel + suppress(CancelledError)
- [x] `tests/test_web/test_orphaned_sweep.py` 7/7 (startup 3 + sweep loop 4)

### PR5 — J2.6 결과 영속화 (비-pipeline 포함) ✅ (2026-05-08)
- [x] `_run_job` 의 `result=job.result` 전달은 PR2 에서 이미 구현 — PR5 는 6 job_type 별 직렬화 회귀 검증
- [x] 6 job_type model_dump(mode="json") JSON round-trip 검증:
  - `pipeline` / `analyze` / `generate` / `validate` (application/models) — Path → str / datetime → ISO 정상
  - `brand_card_render` (RenderedCardSet + nested RenderedBrandCard) — manifest_path/png_path/created_at 모두 친화
  - `ranking_bulk_check` (RankingCheckSummary) — primitive only, 직렬화 안전
- [x] `tests/test_web/test_result_serialization.py` 8/8 — 6 모델 round-trip + _persist_status succeeded/failed result kwarg 검증
- [x] **추가 코드 0** — PR2 의 `_persist_status(result=...)` 가 6 job_type 모두 커버. 직렬화 보강 불필요
- [x] commit `feat(ops): Phase J2 PR5 — 결과 영속화 + 비-pipeline 직렬화 회귀`

### J2 종료 검증 (PR5 완료 후)
- [x] `pytest tests/test_web` 208/208 ✅, ruff/format/pyright 그린
- [ ] **사용자 작업** — staging 강제 재시작 테스트: Render Dashboard 에서 `JOB_PERSISTENCE_ENABLED=true` 토글 + Manual Deploy → orphaned 마킹 / GET 200 OK / 통합 알림 검증
- [ ] **사용자 작업** — 운영 1주 모니터링: DB write latency p99 + Supabase row growth + orphaned 발생 빈도 → grace 5분 적정성 판단 → Phase J3 (Worker 분리) 착수 결정

---

## ⚠️ Phase J 위험 요소

- **DB write 가 응답 latency 추가**: `submit_*` 만 동기 insert (~100ms). status update / heartbeat / progress_events 는 fire-and-forget + 실패 logger.warning. 임계 초과 시 `_submit` 도 background insert 로 전환
- **progress_events 테이블 폭주**: 단계별 이벤트가 분당 수십 건. 7일 retention cron + PK `(job_id, seq)` + 인덱스 `(created_at)`. PR3 에서 retention 정책도 같이 결정 (Phase J 후속)
- **false orphaned**: heartbeat grace 5분. 더 짧으면 정상 job 도 orphaned 처리 위험. PR4 첫 24h grace 15분 → 운영 데이터 누적 후 단축
- **Supabase 장애 graceful degrade**: 모든 DB call 은 try/except + logger.warning. notifier 패턴 그대로 — 알림 끊겨도 본 흐름 동작 (graceful)
- **격리 위반 우려 (`WebSocketProgressReporter` ↔ DB)**: reporter 가 DB 직접 write 하면 application 레이어 격리 깨짐. PR3 에서 `event_bus.emit` 내부 hook 으로 처리하거나 job_manager 가 별도 subscribe — reporter 는 이벤트 발행만
- **단일 흐름 보호**: `application/orchestrator.run_pipeline` / `run_analyze_only` / `run_generate_only` 시그니처 절대 무변경. 변경 영역은 `web/api/job_manager.py` + 신규 `web/api/job_store.py` + 신규 schema + `config/settings.py` flag 만
- **rollout 단계**: PR2 staging flag on → 1일 관찰 → PR3 / PR4 / PR5 단계 진행. flag off 회귀 테스트 필수 (모든 PR 의 vitest/pytest 에 포함)

## 🔮 Phase J 후속 (별도 todo 진입 시 분해)

> **2026-05-08 J2 종료 시점 검토 결과 (J3 검토 세션)** — J3 / J4 / J5 모두 1주 모니터링 데이터가 누적되어야 우선순위 정함. J2 staging 활성화 + 1주 데이터 (latency p99 / orphaned 빈도 / job_type 별 메모리 피크) 후 결정 게이트.
>
> **재검토 일자**: 2026-05-15 (J2 staging 활성 후 1주)

- **Phase J3 — Worker 분리**: API stateless + Render Background Worker. Postgres `FOR UPDATE SKIP LOCKED` 큐 (SPEC-BATCH `claim_item_for_dispatch` 패턴 재사용). 비용 ~$7/mo, 운영 복잡도 ↑. **착수 조건**: 1주 데이터에서 API process 가 OOM 또는 응답성 한계로 확인되고, 단일 job_type 이 아닌 여러 job_type 에서 메모리 피크가 분산된 경우
- **Phase J4 — Playwright 격리**: 브랜드 카드 렌더만 별도 서비스 (Vercel Sandbox 또는 Browserless). API/Worker 메모리 200~300MB 절감. **착수 조건**: 1주 데이터에서 brand_card_render 가 OOM 트리거의 주범으로 확인 (2026-05-08 사고의 직접 원인이라 가설 우세). 비용 저렴, 복잡도 중. **J3 보다 ROI 높을 가능성 ↑**
- **Phase J5 — Durable workflow**: Inngest 또는 Temporal. 의료법 fixer/이미지 재시도/약한 섹션 보강을 step 단위 체크포인트화. 도입 시점은 J2~J4 안정화 + 운영 데이터 누적 후 trade-off 평가

### 1주 모니터링 체크리스트 (사용자 작업)
- [ ] Render Dashboard env: `JOB_PERSISTENCE_ENABLED=true` 활성화 (PR1~PR5 commit 후 schema 마이그레이션 적용 완료)
- [ ] 1주간 관찰:
  - [ ] DB write latency: `_submit` 의 동기 insert_job p99 < 200ms
  - [ ] Supabase row growth: `progress_events` 테이블 크기 → 7일 retention cron 필요 시점 판단
  - [ ] orphaned 발생 빈도: 컨테이너 재시작 빈도 + 이번 환경에서 grace 5분 적정성
  - [ ] job_type 별 메모리 피크 (Render metrics): pipeline / generate / brand_card_render / ranking_bulk_check 별 RAM peak
- [ ] 2026-05-15 결정 게이트: J3 vs J4 우선순위 / 보류 / 통합 진행


---

## /insights 페이지 + failure_category enum (2026-05-14)

> 목표: 운영자가 "어떤 키워드가 왜 상위노출이 안 되는가" 를 한 화면에서 확인.
> 발행 후 미노출은 `visibility_diagnoses` 5종으로 이미 가능하지만, **분석 단계 실패 사유**는
> `keyword_batch_items.error` 자유 텍스트라 집계 불가능. 이를 enum 으로 정규화하고
> `/insights` 에 키워드 단위 통합 행 뷰를 추가한다.

### 사용자 확정 사항
- **`/insights` 노출 범위**: 전체 키워드 (분석/미발행/노출/미노출 모두 1행씩). 운영자가 한 화면에서 전체 상태 파악
- **`failure_category` 적용 범위**: 신규 row 부터 enum 라우팅 + **기존 error 텍스트 정규식 백필 1회성 스크립트** 필수

### 사전 조사 결과 (read-only 탐색 완료)
- 기존 `/insights` 는 RSC + `InsightsClient` 의 **summary 통계 dashboard** (`application/insights_orchestrator.py::get_insights_summary`). 이번 작업은 **키워드 단위 행 뷰** — 같은 페이지에 탭 추가 또는 `/insights/keywords` sub-route 로 분리 (B3 에서 결정)
- nav 6영역 구조 확정 (`web/frontend/src/components/NavBar.tsx`): 운영 홈 / 생성 / 검수·발행 / 성과·분석 / 브랜드 / 관리. `/insights` 는 이미 "성과·분석" 하위 sub-link → **추가 nav 작업 불필요**, 같은 entry 안에서 뷰 확장만
- `labels.ts` 단일 출처 + `VOLUME_LABELS`/`DIFFICULTY_LABELS`/`DIAGNOSIS_LABELS`/`BATCH_ITEM_LABELS` 등 7매핑 존재. `FAILURE_CATEGORY_LABEL` 만 추가하면 정합
- `_handle_item_failure(item, exc)` (`application/batch_orchestrator.py:750~787`) — 예외 타입 → enum 매핑 진입점. `err_msg = f"{type(exc).__name__}: {exc}"` 다음 줄에 enum 추출 추가
- `_apply_prefilter` (455~509) — `reasons` 리스트에 `search_volume=...` 또는 `difficulty=...` 키워드로 분기 식별 가능
- `storage.update_item_status` / `update_item_result` 양쪽 모두 partial update 패턴 (None=변경 안 함). `failure_category` 컬럼은 `update_item_status` 에 파라미터 추가가 가장 자연스러움 (status 와 같이 갱신)
- 실제 raise 되는 예외 타입 확정:
  - `InsufficientCollectionError` (`domain/crawler/model.py:71`) — stage="serp" / stage="scrape" 두 경로
  - `prefilter:` prefix (`_apply_prefilter` line 496) — `search_volume=N<min` / `difficulty=GRADE>max` 두 경로
  - `ComplianceFailed` 류 — `domain/compliance` 의 fixer 2회 실패 시 `RuntimeError` 또는 SPEC §3 [8] 종료 (정확한 예외명은 A1 구현 시 다시 grep)
  - `본문_차별화_부족` — cluster reuse Jaccard 초과, `compliance_violations` 에 라벨 push (line 297). 예외 raise 아님 → `_dispatch_item` 본문 분기에서 직접 마킹
  - 그 외 모두 → `EXCEPTION`
- `web/api/routers/insights.py` 이미 존재 — 같은 prefix 에 `/keywords` endpoint 추가만

### 제약/원칙 (반복)
- 단일 흐름 시그니처 무변경 (Pydantic nullable 필드 + 새 컬럼만 허용)
- domain/ 신규 도메인 신설 X (`application/insights_view.py` 는 use case 계층, **기존 `insights_orchestrator.py` 와 분리** — 책임 차이: orchestrator=통계 집계 / view=행 단위 join 뷰)
- LLM 호출 신규 추가 X (모두 SQL + 코드 룰)
- 라벨/문구는 `lib/labels.ts` 단일 출처
- `FailureCategory` enum 변경 시 `CLAUDE.md` 변경이력에 기록 의무
- 의료법 컨텍스트 무관 (`compliance_violations` 는 그대로, 분석 단계에서는 `failure_category=COMPLIANCE_FAILED` 만 마킹)
- pyright strict 통과, pytest 회귀 0 fail

### Phase A: failure_category enum (1순위)

- [ ] **A1** `domain/batch/model.py` 에 `FailureCategory` Literal 추가 — 7종 (`PREFILTER_VOLUME`/`PREFILTER_DIFFICULTY`/`SERP_INSUFFICIENT`/`SCRAPE_INSUFFICIENT`/`COMPLIANCE_FAILED`/`BODY_SIMILARITY_HIGH`/`EXCEPTION`). `KeywordBatchItem` 에 `failure_category: FailureCategory | None = None` 필드 추가. 도메인 격리 원칙 준수 (다른 도메인 import 0). 검증: pyright 통과 + 기존 KeywordBatchItem 직렬화 테스트 회귀 0
- [ ] **A2** `config/schema.sql` 의 `keyword_batch_items` 정의에 `failure_category text` 컬럼 추가 + 별도 alter SQL 블록 (`-- 2026-05-14 failure_category 컬럼 추가` 주석). 부분 인덱스 `create index if not exists idx_kbi_failure_cat on keyword_batch_items (status, failure_category) where status in ('failed','skipped')`. 검증: Supabase SQL Editor dry-run + `\d keyword_batch_items` 컬럼 확인
- [ ] **A3** `application/batch_orchestrator.py` 라우터 변경 — (a) `_apply_prefilter` 의 미달 분기에서 `reasons` 첫 항목 검사해 `PREFILTER_VOLUME`/`PREFILTER_DIFFICULTY` 결정 → `update_item_status` 에 전달. (b) `_handle_item_failure` 에서 `_classify_exception(exc)` 헬퍼 신설 (예외명 isinstance + 메시지 prefix 분기로 7종 매핑) → `update_item_status` 에 전달. (c) `_dispatch_item` 본문 차별화 분기 (line 296) → `BODY_SIMILARITY_HIGH` 마킹. **기존 error 텍스트는 그대로 유지** (사람용 디테일). 검증: 단위 테스트 (A6) + 기존 `_handle_item_failure` 테스트 회귀
- [ ] **A4** `domain/batch/storage.py::update_item_status` 시그니처에 `failure_category: FailureCategory | None = None` 파라미터 추가, partial update payload 에 포함. status 가 'failed'/'skipped' 가 아닌 경우 (queued 복귀 등) 자동 NULL clear (error 컬럼과 동일 패턴). 검증: storage 단위 테스트
- [ ] **A5** `scripts/backfill_failure_category.py` 신규 — 1회성 — `status IN ('failed','skipped') AND failure_category IS NULL` row 만 fetch → 정규식 매칭 → enum 매핑. `--dry-run` 기본, `--apply` 옵션으로만 실제 update. 매칭 안 되는 row 는 카운트 로깅 (수동 검토 대상). 패턴: `^prefilter:.*search_volume` → PREFILTER_VOLUME, `^prefilter:.*difficulty` → PREFILTER_DIFFICULTY, `InsufficientCollectionError:\s*serp` → SERP_INSUFFICIENT, `InsufficientCollectionError:\s*scrape` → SCRAPE_INSUFFICIENT, `ComplianceFailed|compliance.*failed` → COMPLIANCE_FAILED, `본문_차별화_부족` → BODY_SIMILARITY_HIGH, 나머지 → EXCEPTION. 검증: `--dry-run` 출력에 카운트 + 매칭 안 된 샘플 5개 print
- [ ] **A6** `web/frontend/src/lib/labels.ts` 에 `FAILURE_CATEGORY_LABELS` + `getFailureCategoryLabel(category)` 추가 (한글 라벨). 권장액션 텍스트는 별도 `FAILURE_CATEGORY_RECOMMENDED_ACTION` + `getFailureCategoryRecommendedAction()` (B1 의 통합 권장액션 매퍼와 별도 — 백엔드에서 채워서 내려보내고 프론트는 단순 표시. 본 헬퍼는 fallback 용). 검증: 기존 `labels.test.ts` 패턴으로 7케이스 매칭
- [ ] **A7** tests — (a) `tests/test_batch/test_failure_category.py`: 7종 enum 라우팅 단위 테스트 (mock storage, `_classify_exception` + `_apply_prefilter` 각 케이스). (b) `tests/test_scripts/test_backfill_failure_category.py`: 정규식 매칭 7케이스 + 매칭 실패 케이스. (c) 기존 `tests/test_batch/test_batch_orchestrator.py::test_apply_prefilter*` 의 어서션 갱신 (`failure_category` 컬럼 함께 검증). 검증: `pytest tests/test_batch tests/test_scripts --no-cov` 회귀 0

### Phase B: /insights 키워드 행 뷰 (2순위)

- [ ] **B1** `application/insights_view.py` 신규 (insights_orchestrator 와 분리 — 책임: 통계 vs 행 뷰). `list_keyword_insights(*, status_filter, failure_category, diagnosis_category, batch_id, page, limit)` → `list[KeywordInsightRow]` + `total`. 반환 모델 `KeywordInsightRow` Pydantic — 컬럼: keyword, search_volume, difficulty_grade, analysis_status (`pending`/`succeeded`/`skipped`/`failed`/`needs_review`/`ready_to_publish`), failure_category, failure_category_label, publication_status (`not_published`/`published`/`republished`), latest_rank_position, latest_rank_section, diagnosis_category, diagnosis_confidence, **recommended_action** (4가지 출처 통합 — 분석실패=failure_category 라벨, 미발행="발행 진행", 미노출=diagnosis.recommended_action, 정상=빈 칸), batch_id, item_id, pattern_card_id, publication_id. SQL: PostgREST select 가 multi-table left join 미지원이므로 **3차례 fetch + python merge** (keyword_batch_items → publications by keyword → 최신 visibility_diagnoses by publication_id → 최신 ranking_snapshots). 또는 Supabase RPC SQL view 1개 신설 (성능 측정 후 결정 — 1차 구현은 fetch+merge, 운영 누적 1000건 이상 시 RPC 검토). 검증: 단위 테스트 (B5) + 빈 데이터 graceful
- [ ] **B2** `web/api/routers/insights.py` 에 `GET /insights/keywords` endpoint 추가 (기존 `/insights/summary` 와 동거). 쿼리 파라미터: `status` / `failure_category` / `diagnosis_category` / `batch_id` / `page` (default 1) / `limit` (default 50, max 200). 응답: `{rows: KeywordInsightRow[], total: int, page: int, limit: int}`. 검증: API 통합 테스트 (B5)
- [ ] **B3** `web/frontend/src/app/insights/page.tsx` + `InsightsClient.tsx` 에 **탭 UI** 추가 — "통계 요약" (기존 summary dashboard) / "키워드 단위" (신규). 같은 라우트 `/insights?tab=keywords` 로 deeplink 지원. 신규 탭 컴포넌트는 별도 파일 `InsightsKeywordsView.tsx` (RSC 진입은 page.tsx, client useSWR 는 컴포넌트 안). 컬럼: 키워드 | 검색량 | 난이도 | 분석상태 | 실패사유 | 발행상태 | 최근순위 | 최근진단 | 권장액션. 필터 UI: 상태별 칩 (전체/분석실패/미발행/미노출/자기잠식/순위하락/정상노출). 페이지네이션 (50/페이지). row 클릭 → `pattern_card_id` 있으면 `/patterns/by-id/[id]`, `publication_id` 있으면 `/rankings/[id]`. `lib/labels.ts` 라벨 사용. 검증: vitest 렌더링 + 필터 토글
- [ ] **B4** ~~nav 진입~~ — **불필요**. nav 6영역의 "성과·분석 > 인사이트" 가 이미 `/insights` 로 진입. 탭 추가만 (B3) 으로 충족
- [ ] **B5** tests — (a) `tests/test_application/test_insights_view.py`: 각 출처 분기 검증 (분석실패/미발행/미노출/정상 4케이스 + recommended_action 통합 매퍼). (b) `tests/test_web_api/test_insights_router_keywords.py`: 필터/페이지네이션 + 200 응답 shape. (c) `web/frontend/src/app/insights/__tests__/InsightsKeywordsView.test.tsx` (vitest): 칩 토글 + row 클릭 라우팅 (mock router) + labels 함수 호출 매칭. 검증: `pytest tests/test_application/test_insights_view.py tests/test_web_api/test_insights_router_keywords.py --no-cov` + `pnpm -C web/frontend test --run InsightsKeywordsView`

### Phase C: 사유별 집계 (후속, 이번 SPEC 미포함)

- [ ] **C1** 도넛 차트 — `failure_category` 분포 (전체 batch 합산) — recharts 또는 sparkline 검토
- [ ] **C2** 요약 카드 — Top 3 실패 사유 + 직전 7일 추이 + click → /insights?failure_category=X 필터 적용

### Phase D: 발행 전 위험 스코어 (후속, 이번 SPEC 미포함)

- [ ] **D1** LOW/MED/HIGH 라벨 룰 정의 — difficulty + search_volume + cluster 본문 차별화 예측
- [ ] **D2** publication 등록 직전 위험도 카드 표시 + 운영자 confirm 게이트

### 리스크 / 완화

- **R1**: 기존 error 텍스트와 failure_category 불일치 (백필 후 신규 코드 변경 시 동일 케이스가 다른 enum 으로 마킹) → 완화: A3 의 분기 로직과 A5 의 정규식이 **동일 키워드** 사용하도록 동일 모듈 (`domain/batch/model.py`) 에 헬퍼 export. A7 테스트가 두 경로 cross-check
- **R2**: PostgREST left join 미지원으로 B1 의 fetch+merge 성능 — 운영 row 1000건 이상 시 N+1 위험. 1차는 batch fetch (in.(...)) 로 round-trip 4회 이내 고정. 1000건 초과 시 RPC view 신설 (C 와 같이 검토)
- **R3**: 백필 스크립트 오작동으로 잘못된 enum 마킹 → 완화: `--dry-run` 기본 + 매칭 안 된 row 카운트 강제 표시 + `--apply` 명시 시에만 update. 1회성이므로 멱등성보다 사람 검토 우선
- **R4**: `failure_category` 컬럼 미배포 환경 (로컬 dev) graceful — A4 의 update_item_status 가 Supabase 오류 시 컬럼 빼고 retry (기존 `compliance_violations` 패턴 차용)
- **R5**: 🔴 백필 스크립트는 production DB 에 직접 write → A5 구현 시 `--apply` 는 환경변수 `BACKFILL_CONFIRM=YES` 이중 가드 필수

### 완료 조건 (Acceptance)

- A 완료: 신규 batch 실행 후 `keyword_batch_items.failure_category` 컬럼이 7종 enum 중 하나로 채워짐 (실패/skipped row 한정). 백필 스크립트 `--dry-run` 으로 기존 row 매칭률 80%+ 확인
- B 완료: `/insights?tab=keywords` 페이지에서 키워드 1행 = 분석/발행/순위/진단 통합 1행으로 표시. 칩 필터로 "분석실패만" / "미노출만" 토글 가능. row 클릭 → 해당 PatternCard 또는 Publication 으로 진입
- pytest/pyright 회귀 0 fail. 단일 흐름 시그니처 무변경 (KeywordBatchItem Pydantic nullable 필드 + DB 컬럼만 추가)

---

# insane-search 하이브리드 fetcher 통합 — 2026-07-06 계획

> 목표: Bright Data(Web Unlocker, 유료) 비용 절감을 위해 오픈소스 insane-search 의
> `curl_cffi` fetch 엔진을 **본문 수집 경로에만** 부분 도입한다. IP 로테이션이 없는
> insane 의 한계를 **폴백 있는 하이브리드**로 흡수한다.
> SPEC 참조: SPEC-SEO-TEXT.md §3 [1][2] (크롤러 도메인), §12 (application 레이어)
> 실측 결론 (확정): 본문(m.blog.naver.com) = insane 120건 단일 IP 무차단 100% + 파서 필드
> 100% 일치 → 무손실 대체 가능. SERP(search.naver.com) = insane WAF 검증기가 challenge
> 오판 → Bright Data 유지.
> **소스 핀 (확정): insane-search v0.9.1**. 벤더 소스 clone 위치 =
> `C:\Users\assag\AppData\Local\Temp\claude\C--Users-assag-solution-contents-creator\e4d28f8e-d1fe-48a1-9b81-635a661588ec\scratchpad\insane-search\skills\insane-search\engine\` (실사 완료).
> 내부 import 100% 상대 import → 폴더 rename 자유, 내부 코드 무수정으로 반입 가능.

## 🎯 목표 / 비목표

**목표**
- 본문 수집([2] `page_scraper.scrape_pages`) 을 `FallbackFetcher(insane → brightdata)` 로 구성해
  1차 insane(cost=0), 실패 시 Bright Data 자동 폴백.
- `domain/crawler` 에 `HtmlFetcher` Protocol 을 도입해 fetch 계약(`fetch(url)->str` + `close()`
  + `__enter__/__exit__` — **4종 전부**)을 추상화. `BrightDataClient` 는 무변경으로 구현체가 됨
  (이미 4종 보유 — 테스트 StubClient 로 확인). InsaneFetcher/FallbackFetcher 는 4종을 모두 구현해야
  pyright 가 구현체로 인정(누락 시 추상 간주 → 인스턴스화 실패).
- 본문 fetcher 는 settings 토글(`crawler_body_fetcher`)로 "insane"/"brightdata" 강제 전환 가능.
- 기존 crawler regression 테스트(BrightData mock) **무변경 통과** 유지.

**비목표 (이번 범위 아님, 명시)**
- ❌ SERP 수집(`collect_serp`, `keyword_difficulty`, `ranking`) 대체 — Bright Data 그대로 유지.
- ❌ insane IP 로테이션 확보 — 없음. 단일 IP 라 고동시성/장시간은 폴백으로만 흡수.
- ❌ insane Phase 3(Playwright) 활성 — `enable_playwright=False` 런타임 비활성. 코드 물리 삭제는 후속.
- ❌ Bright Data 키 제거 — 폴백용으로 여전히 필수(프리플라이트 무변경).
- ❌ `application/orchestrator.py` 단일 흐름 4함수 시그니처 변경.

## 🧭 핵심 설계 결정 (착수 전 확정 — 사용자 지정 A~G)

> **A. 벤더링 위치 — `vendor/insane_search/` (repo 루트 신규 패키지) 채택**
> - 현재 repo 에 `vendor/` 없음(확인). 최상위에 신규 생성.
> - 사유: insane 을 **외부 라이브러리**로 취급 → domain 순수성 서사 보존(vendor 는 도메인 아님).
>   `architecture-check.sh` 는 `domain/` 만 스캔하므로 `from vendor.insane_search...` 는 검사 대상 밖.
>   대안 `domain/crawler/_vendor/` 는 자동 패키징/COPY 되나 "도메인 안에 외부코드" 로 순수성 흐림 → 기각.
> - 대가(추가 작업 3건, 아래 PR2 에 반영): (1) `pyproject.toml [tool.setuptools.packages.find] include` 에
>   `"vendor*"` 추가(= domain 의 `from vendor...` pyright resolve 관건), (2) `Dockerfile` **의존성 레이어에 vendor
>   placeholder 선배치**(setuptools strict-editable finder 등록) + 코드 COPY 단계에 `COPY vendor/ vendor/` + Docker 내
>   import 스모크(현재 domain/application/config/web 만 명시 COPY), (3) `ruff extend-exclude` 에 `vendor` 추가
>   (린트 면제). pyright 는 vendor 를 include 밖으로 두므로 별도 제외 불필요 — 진짜 관건은 (1) 의 경로 노출(step9 재프레이밍).
>
> **B. Protocol — `domain/crawler/fetcher.py::HtmlFetcher`**
> - **멤버 4종 전부**: `fetch(url: str) -> str` + `close() -> None` + `__enter__` + `__exit__`.
>   InsaneFetcher·FallbackFetcher 가 이 4종을 모두 구현해야 pyright 가 Protocol 구현체로 인정(하나라도
>   누락 시 추상 클래스 간주 → 인스턴스화·주입 실패).
> - **성공 판정 계약**: 구현체는 vendor `FetchResult.ok: bool` 를 성공의 단일 신호로 삼는다. verdict 문자열
>   열거로 성공/실패를 재구성하지 않는다.
> - 예외 계약: 실패 시 `BrightDataError` 계열(특히 재시도/폴백 유도는 `BrightDataTransientError`) 호환 예외를
>   raise. (기존 `brightdata_client.py` 의 3계층 예외를 계약 표준으로 재사용.)
> - `BrightDataClient` 는 이미 4종 보유 → 코드 변경 없이 구현체.
>
> **C. 어댑터 — `domain/crawler/insane_fetcher.py::InsaneFetcher`**
> - **vendor fetch() 실제 시그니처 (실사 확정, v0.9.1 fetch_chain.py:348)**:
>   `fetch(url, *, success_selectors=None, device_class="auto", user_hint=None, timeout=25,
>   max_attempts=None, max_browser_attempts=2, enable_playwright=True, enable_phase0=True,
>   enable_learning=True) -> FetchResult`.
> - **어댑터 호출 규약 (고정)**: `enable_playwright=False`(필수 — curl-only 격리, executor/Playwright import 차단),
>   `enable_learning=False`(필수 — 홈디렉터리 학습파일 쓰기 차단), `device_class="mobile"`(본문 m.blog).
>   `enable_phase0` 는 engine default(True) 유지(실사로 존재 확인). `device_class`·`enable_phase0` 는
>   **실존 파라미터** — mock 만으로는 오타/시그니처 오류를 못 잡으므로 PR3 완료 게이트에 실 vendor 1-URL 스모크 추가.
> - **성공 판정 재작성 (verdict 열거 폐기)**:
>   - `if not result.ok: <처리>`. `ok=True`(strong_ok/weak_ok) → content 채택.
>   - `ok=False` 실패 verdict 5종 = challenge / blocked / rate_limited / auth_required / not_found.
>     `TERMINAL_NONSUCCESS = {auth_required, not_found, rate_limited}`(engine 즉시 종료, 실사 validators.py:84 확인).
>   - **suspect_ok(부분성공)**: `ok=False` 지만 content 가 존재할 수 있음 → **content sanity(최소 길이 +
>     차단마커 부재) 통과 시에만 채택**, 아니면 폴백.
>   - suspect_ok 외 모든 `ok=False` → `BrightDataTransientError` 호환 예외 raise(폴백 유도).
> - 🔴 **명시적 결정**: **모든 insane 실패는 폴백한다. not_found(404) 는 Bright Data 도 404 라 폴백이 유료
>   낭비이나, verdict 별 분기로 낭비를 특례 처리하지 않고 "낭비 감수 + 단순성" 을 채택**(부분 성공 케이스가
>   verdict 오판일 위험 > 404 낭비 비용).
> - **tenacity 재시도 = 1회로 최소화**(폴백이 있으므로 insane 자체 재시도 증폭 불필요) + 타임아웃 필수.
> - **동시성 세마포어 실배선**: module-level `threading.BoundedSemaphore(settings.insane_concurrent_limit)` 를
>   두고 `fetch()` 에서 `with _semaphore:` acquire. `brightdata_client.py` 의 `_concurrent_semaphore` 패턴 미러.
>   (근거: 배치 BATCH_MAX_WORKERS 2~3 이 단일 IP insane 을 동시 타격 → 강제 메커니즘 없으면 설정값 no-op.)
> - **usage**: **성공 시에만** `record_usage(ApiUsage(provider="insane"))`(cost=0). 실패(폴백 유도) 시 미기록.
> - **close()**: curl_cffi 세션 자원(transport 세션풀) 해제 명세.
>
> **D. 폴백 — `domain/crawler/fallback_fetcher.py::FallbackFetcher(primary, fallback)`**
> - HtmlFetcher 4종 전부 구현: `fetch`/`close`/`__enter__`/`__exit__`.
> - `primary.fetch(url)` 실패(BrightDataError 계열) 시 `fallback.fetch(url)` 호출.
> - **usage 이중집계 차단**: FallbackFetcher 는 `record_usage` 를 **호출하지 않는다**. 폴백 발생은
>   `logger.warning` 만 남긴다. 성공 usage 는 primary(insane) 또는 fallback(BrightDataClient) 이 각자 기록.
>   폴백률은 `provider=brightdata` + `stage=page_scraping` usage 분포로 추론.
> - `close()`·`__exit__` 는 primary·fallback 양쪽에 위임.
>
> **E. 라우팅 — 팩토리 분기**
> - 본문 경로(`run_stage_page_scraping`) ← `FallbackFetcher(InsaneFetcher, BrightDataClient)` 주입.
> - SERP 경로(`run_stage_serp_collection`, `keyword_difficulty`, `ranking`) ← `BrightDataClient` 유지.
> - settings 토글 `crawler_body_fetcher`(default "insane") + `insane_concurrent_limit=3`(단일 IP 보수적,
>   C 의 세마포어로 실제 강제) + `insane_timeout_seconds`.
> - ⚠️ **재시도 증폭 주의**: `page_scraper.scrape_pages` 는 이미 실패 URL 을 1회 batch 재시도한다. 이 재시도는
>   `_fetch_one` 를 다시 호출 → **폴백 체인 전체(InsaneFetcher + BrightDataClient)를 다시 돈다**. InsaneFetcher
>   tenacity 1회 + BrightDataClient tenacity 3회 결합 시, 지속 실패 URL 1건 worst-case = insane 2회 + brightdata
>   6회(유료). insane 재시도를 1회로 묶어 insane IP 타격·유료 폭증을 억제.
>
> **F. usage/비용 — provider="insane"(cost=0)**
> - `application/usage_tracker.py::estimate_cost` 에 `provider=="insane"` → 0.0 분기.
>   폴백 시 brightdata usage 는 `BrightDataClient` 내부 `record_usage` 로 기존대로 기록됨(FallbackFetcher 는 무기록).
>
> **G. 테스트 — 어댑터/폴백/라우팅 유닛 + regression 무변경 + 실 vendor 1-URL 통합 스모크(PR3 게이트).**

## 🔴 거버넌스/문서 갱신 — 사용자 승인 완료 (둘 다 갱신)

**본 작업은 아래 governance 문서의 현행 서술과 충돌한다. 사용자가 두 문서 모두 갱신 승인 → 코드와 동반 착지한다.**

- `domain/crawler/CLAUDE.md` §금지 — "Scrapling, Playwright, **기타 대체 크롤링 라이브러리 사용 금지
  (Bright Data 로 통일)**" → insane(curl_cffi) 도입과 직접 충돌. 이 라인 갱신(insane 하이브리드 예외 명기).
- `domain/crawler/CLAUDE.md` §핵심규칙 #1 "모든 Bright Data 호출은 brightdata_client.py 경유" 는
  insane 이 Bright Data 호출이 아니므로 literal 위반 아님. "본문은 HtmlFetcher 추상화 경유" 로 재서술.
- `SPEC-SEO-TEXT.md` §3 [2] + §"기술 스택" + 아키텍처 표(본문 수집을 Web Unlocker 로 서술한 라인) 가 본문 수집
  = Bright Data Web Unlocker 로 서술. 하이브리드(본문 = insane + Bright Data 폴백)로 갱신 — **사용자 승인됨**.
- 🔴 **착지 시점 = PR4(본문 활성화)와 동반** — 코드가 자기 거버넌스 문서를 위반하는 과도기를 만들지 않기 위해,
  거버넌스 갱신(CLAUDE.md + SPEC-SEO-TEXT.md §3[2] + 아키텍처 표)을 **PR5 가 아니라 PR4 에서 코드와 함께 착지**.

## 📌 교체 지점 (현재 코드 기준 재확인 완료)

| 위치 | 현재 | 변경 |
|---|---|---|
| `domain/crawler/brightdata_client.py` | `BrightDataError`/`ClientError`/`TransientError` 3계층, `fetch/close/__enter__/__exit__` | **무변경**. Protocol 이 예외 계약 참조 + 구현체 |
| `domain/crawler/serp_collector.py:85` | `collect_serp(keyword, client: BrightDataClient)` | 타입힌트만 `HtmlFetcher` 로 완화. 로직 무변경(SERP=BrightData 유지) |
| `domain/crawler/page_scraper.py:59,106` | `scrape_pages`/`_fetch_one`(client: BrightDataClient) | 타입힌트 `HtmlFetcher` 완화 + `BrightDataError` catch 는 그대로(폴백은 상위 FallbackFetcher) |
| `application/stage_runner.py:104,130,172` | `_build_brightdata_client()` → serp+page 공용 | `_build_body_fetcher()` 신규(본문 전용). serp 는 기존 유지 |
| `application/keyword_difficulty_orchestrator.py:40` | `_build_client()` | **무변경**(SERP) — "건드리지 않음" 명시 |
| `application/ranking_orchestrator.py:439` | `BrightDataClient(...)` 직접 | **무변경**(SERP) — "건드리지 않음" 명시 |
| `domain/ranking/*` | `Callable[[str],str]` DI | **무변경** — 건드리지 않음 |
| `config/settings.py` | `bright_data_*`, `brightdata_concurrent_limit=5` | insane 토글/동시성/타임아웃 필드 추가 |
| `application/usage_tracker.py:62` | provider brightdata/anthropic/gemini | `insane`(0) 분기 추가 |
| `application/orchestrator.py:560` | `_preflight_required_keys(need_bright_data=...)` | **무변경** — 폴백용 Bright Data 키 여전히 필수(주석만 보강) |
| `pyproject.toml` / `Dockerfile` / `pyrightconfig.json` | vendor 미인지 | `packages.find include "vendor*"` + ruff extend-exclude `"vendor"` + Dockerfile **의존성 레이어에 vendor placeholder 선배치**(setuptools strict-editable finder 등록) + `COPY vendor/` + Docker 내 vendor import 스모크 |

---

## 단계별 체크리스트 (PR 단위)

### PR1 — HtmlFetcher Protocol 도입 + 타입힌트 완화 (동작 무변경, 안전 기반)

- [ ] 1. [`domain/crawler/fetcher.py`] **신규** — `HtmlFetcher` `Protocol` 정의: **멤버 4종 전부**
      `fetch(url: str) -> str`, `close() -> None`, `__enter__`, `__exit__`. docstring 에 "성공 판정 계약:
      구현체는 `FetchResult.ok` 를 성공의 단일 신호로 삼는다(verdict 문자열 열거 금지)" + "예외 계약: 실패 시
      `BrightDataError` 계열, 폴백/재시도 유도는 `BrightDataTransientError`" 명시. `@runtime_checkable` 부여
      (테스트 isinstance 용). 완료 기준: pyright 0, 30줄 이내, 4종 멤버 시그니처 완비.
- [ ] 2. [`domain/crawler/serp_collector.py`] `collect_serp(keyword, client: BrightDataClient)` →
      `client: HtmlFetcher`. import 추가(`from domain.crawler.fetcher import HtmlFetcher`). 로직 무변경.
      완료 기준: 기존 `test_serp_collector.py` 무변경 통과.
- [ ] 3. [`domain/crawler/page_scraper.py`] `scrape_pages`/`_fetch_one` 의 `client: BrightDataClient` →
      `HtmlFetcher`. `BrightDataError` catch 유지. 완료 기준: 기존 `test_page_scraper.py`(StubClient) 무변경 통과.
- [ ] 4. 검증 — `ruff check domain/crawler` + `pyright domain/crawler` + `pytest tests/test_crawler --no-cov` 그린.
      완료 기준: 3개 모두 0 에러, 동작 변화 0.

> PR1 경계: Protocol + 타입 완화만. 벤더/어댑터/라우팅 없음. 순수 리팩터라 롤백 위험 최소.

### PR2 — insane engine 벤더링 (외부 라이브러리 취급, 런타임 미연결)

- [ ] 5. 🔴 [`vendor/insane_search/`] **신규 디렉터리** — insane-search **v0.9.1** engine 반입.
      소스 = `<scratchpad>/insane-search/skills/insane-search/engine/`(clone 확인, 상단 소스 핀 경로).
      **실사 확정 최소집합 = 10개 .py** (`__init__`/`fetch_chain`/`validators`/`waf_detector`/`url_transforms`/
      `content_safety`/`transport`/`safety`/`learning`/`phase0`) **+ `waf_profiles.yaml`**. **`executor.py`·
      `templates/`·`__main__.py`·`bias_check.py`·`tests/` 제외**(enable_playwright=False 면 executor import 자체가
      안 일어남). + `vendor/__init__.py` + `vendor/insane_search/__init__.py`. 내부 100% 상대 import → 폴더 rename
      자유·내부 무수정. MIT 라이선스 파일 동봉. 완료 기준: 디렉터리 존재 + `FetchResult`/`fetch` 심볼 확인.
- [ ] 6. [`vendor/insane_search/**`] import 무결성 확인 — 내부가 **100% 상대 import**(`from .validators ...`)임을
      실사로 확정 → **rename 불필요, 내부 코드 무수정**. 확인만: (a) executor/Playwright 계열이 top-level import 로
      끌려오지 않음(`fetch_chain.py` 가 executor 를 **지연 import**), (b) 제외한 executor.py/templates 를 참조하는
      top-level import 부재. 완료 기준: `python -c "import vendor.insane_search"` + fetch/FetchResult import 예외 0,
      `enable_playwright=False` 경로에서 executor 미로드.
- [ ] 7. [`pyproject.toml`] dependencies — 서드파티는 **curl_cffi(필수, 로컬 0.14.0 확인)** + **pyyaml**
      (waf_profiles.yaml 로드) 추가. **bs4 는 이미 보유**(재사용). Playwright/executor 계열 제외.
      `[tool.setuptools.packages.find] include` 에 `"vendor*"` 추가(현재 `["domain*","application*","config*","web*"]`).
      완료 기준: `pip install -e ".[dev]"` 성공 + `vendor` 패키지가 editable finder 에 등록.
- [ ] 8. [`Dockerfile`] **2곳 수정**: (1) **의존성 레이어**(현재 `RUN mkdir -p domain application config web/api &&
      touch ...__init__.py && pip install -e`)에 `vendor/__init__.py`(+ `vendor/insane_search/__init__.py` 및 필요 최소
      stub) **선배치** — setuptools strict-editable finder 가 `pip install` 시점에 vendor 패키지를 등록하도록(placeholder
      누락 시 editable install 이 vendor 를 못 잡음). (2) 실제 코드 COPY 단계(현재 domain/application/config/web 만
      명시)에 `COPY vendor/ vendor/` 추가. **+ Docker 빌드 내 vendor import 스모크 스텝**
      (`RUN python -c "import vendor.insane_search"`) — 로컬 import 스모크만으로는 Docker 경로 미검증.
      완료 기준: Dockerfile diff 에 placeholder + COPY + import 스모크 3요소 존재.
- [ ] 9. [`pyproject.toml` ruff `extend-exclude`] 에 `"vendor"` 추가(외부코드 린트 면제 — `print()`/bare except 등
      vendor 원본 스타일 허용). **pyright 재프레이밍**: vendor 는 `pyrightconfig.json` include(domain/application/
      config) **밖**이라 "vendor 제외"는 부분 불필요. 진짜 리스크는 `reportMissingImports:"error"` — domain 파일의
      `from vendor.insane_search import ...` 가 resolve 실패하면 에러(exclude 로 안 고쳐짐). → **관건은
      `vendor/__init__.py` 존재 + 경로 노출(`pyproject packages.find include "vendor*"`, step7)**. editable install 로
      import 가능해지면 pyright 도 심볼 resolve. 완료 기준: `ruff check .` 가 vendor 무시 + domain 의 `from vendor...`
      가 pyright `reportMissingImports` 0.
- [ ] 10. 검증 — `python -c "from vendor.insane_search import fetch, FetchResult"` import 클린 + `ruff check .` +
      `pyright`(domain 의 `from vendor...` reportMissingImports 0). 완료 기준: import/lint/type 그린, 런타임 연결 없음.

> PR2 경계: 벤더 반입 + 패키징/배포/린트 배선만. 어댑터/라우팅 없음(아직 아무 코드도 insane 호출 안 함).
> 🔴 되돌리기: vendor 디렉터리 생성은 파일 다수 추가 — 롤백은 디렉터리 삭제 + pyproject/Dockerfile 되돌림.

### PR3 — InsaneFetcher + FallbackFetcher 어댑터 (HtmlFetcher 구현, 라우팅 미연결)

- [ ] 11. [`domain/crawler/insane_fetcher.py`] **신규** — `InsaneFetcher` (HtmlFetcher 4종 구현).
      `fetch(url)` 가 vendor `fetch(url, device_class="mobile", enable_playwright=False, enable_learning=False,
      enable_phase0=True, timeout=settings.insane_timeout_seconds)` 호출(실 시그니처 §C 고정) →
      **성공 판정 = `FetchResult.ok`**:
      - `result.ok` → `content` sanity(최소 길이 + 차단마커 부재) 후 반환.
      - `not result.ok` + `verdict=="suspect_ok"` + content sanity 통과 → 반환(부분성공 채택).
      - 그 외 모든 실패(challenge/blocked/rate_limited/auth_required/not_found, suspect_ok sanity 미달) →
        `BrightDataTransientError` raise(폴백 유도). **verdict 문자열 열거로 성공 재구성 금지**.
      - 🔴 not_found 도 폴백(낭비 감수 — §C 결정).
      **tenacity `@retry` = 1회 재시도로 최소화**(폴백 존재) + 타임아웃. module-level
      `threading.BoundedSemaphore(settings.insane_concurrent_limit)` 를 `fetch()` 에서 `with` acquire
      (brightdata_client `_concurrent_semaphore` 미러). **성공 시에만** `record_usage(provider="insane")`.
      차단마커/최소길이 임계는 모듈 상수(매직넘버 승격). `close()` 는 curl_cffi transport 세션풀 해제.
      완료 기준: 함수 30줄/파일 300줄 이내, HtmlFetcher 4종 완비, 타입힌트 완비.
- [ ] 12. [`domain/crawler/fallback_fetcher.py`] **신규** — `FallbackFetcher` (HtmlFetcher 4종 구현). 생성자
      `(primary: HtmlFetcher, fallback: HtmlFetcher)`. `fetch()` 는 primary 시도 → `BrightDataError` 계열 catch 시
      **`logger.warning`(폴백 발생)만 남기고 `record_usage` 는 호출하지 않음**(이중집계 차단 — 성공 usage 는
      primary/fallback 이 각자 기록) 후 `fallback.fetch()`. `close()`·`__exit__` 는 primary·fallback 양쪽 위임,
      `__enter__` 는 self 반환. 완료 기준: 30줄 이내, HtmlFetcher 4종 완비, record_usage 미호출.
- [ ] 13. [`application/usage_tracker.py:62 estimate_cost`] `if usage.provider == "insane": return 0.0` 분기 추가.
      [`domain/common/usage.py:23`] `ApiUsage.provider` 주석에 `| "insane"` 추가(문서화). 완료 기준: usage 집계에
      insane 0원 반영.
- [ ] 14. [`tests/test_crawler/test_insane_fetcher.py`] **신규** — vendor `fetch` mock(`FetchResult` 반환):
      (a) `ok=True` 정상 content → 반환, (b) verdict=`challenge`(ok=False) → `BrightDataTransientError`,
      (c) verdict=`blocked` → 예외, (d) **verdict=`not_found`(404) → 예외(폴백, 낭비 감수 결정 검증)**,
      (e) **verdict=`auth_required` → 예외**, (f) **verdict=`rate_limited` → 예외**,
      (g) **verdict=`suspect_ok` + content sanity 통과 → 반환(부분성공 채택)**,
      (h) **verdict=`suspect_ok` + 과소길이/차단마커 → 예외(폴백)**, (i) `ok=True` 지만 content 차단마커/과소길이 → 예외,
      (j) timeout/예외 → tenacity 1회 재시도 후 예외, (k) **성공 시 usage provider="insane" 기록 / 실패 시 미기록 어서션**,
      (l) 세마포어 acquire 경로 진입(동시성 가드 존재 확인). 완료 기준: 12+ 케이스 그린.
- [ ] 15. [`tests/test_crawler/test_fallback_fetcher.py`] **신규** — (a) primary 성공 → fallback 미호출,
      (b) primary `BrightDataTransientError` → fallback 호출 + 반환, (c) primary+fallback 모두 실패 → 예외 전파,
      (d) `close()`·`__exit__` 가 둘 다 닫음, (e) **폴백 발생 시 FallbackFetcher 가 `record_usage` 미호출 어서션
      (이중집계 비발생 — record_usage monkeypatch spy)**, (f) `__enter__` self 반환. StubFetcher(HtmlFetcher
      duck-type, record_usage 스파이) 사용. 완료 기준: 6+ 케이스 그린.
- [ ] 16. 🔴 **PR3 완료 게이트** — `pytest tests/test_crawler --no-cov` + `pyright` 그린 **+ 실 vendor 1-URL 통합
      스모크**: 실제 `vendor.insane_search.fetch` 로 m.blog.naver.com 1건 fetch → InsaneFetcher 경유 content 반환
      확인(mock 은 시그니처 오타/실 반환구조 오류를 못 잡음). 스모크는 네트워크 의존 → `@pytest.mark.integration`
      + 기본 skip, 수동/CI opt-in. 완료 기준: 유닛 그린 + 통합 스모크 1회 수동 통과 기록.

> PR3 경계: 어댑터 구현 + 유닛만. stage_runner 라우팅은 아직 BrightData 단독(동작 무변경).

### PR4 — 라우팅 팩토리 분기 + settings 토글 (본문 = insane→brightdata 폴백 활성)

- [ ] 17. [`config/settings.py`] 필드 추가 — `crawler_body_fetcher: str = "insane"`("brightdata" 로 강제 가능),
      `insane_concurrent_limit: int = 3`(단일 IP 보수적 — **PR3 InsaneFetcher 의 module-level BoundedSemaphore 가
      실제 소비**, 정의만 아님), `insane_timeout_seconds: int = 30`. env 매핑/주석 기존 패턴 준수.
      완료 기준: `settings.crawler_body_fetcher` 로드 + insane_concurrent_limit 이 세마포어에 배선됨(no-op 아님).
- [ ] 18. [`config/.env.example`] insane 토글 3필드 예시 추가(동기화). 완료 기준: .env.example 에 키 존재.
- [ ] 19. [`application/stage_runner.py`] `_build_body_fetcher() -> HtmlFetcher` 신규 —
      `crawler_body_fetcher == "insane"` 이면 `FallbackFetcher(InsaneFetcher(...), BrightDataClient(...))`,
      아니면 `BrightDataClient(...)`. `run_stage_page_scraping` 의 `_build_brightdata_client()` →
      `_build_body_fetcher()` 로 교체. `run_stage_serp_collection` 은 `_build_brightdata_client()` **유지**.
      `client: BrightDataClient | None` 파라미터 타입힌트 → `HtmlFetcher | None`. 완료 기준: 본문 경로만 폴백 fetcher,
      SERP 경로 무변경.
- [ ] 20. [`application/orchestrator.py:560`] `_preflight_required_keys` **무변경** — 주석만 보강:
      "본문 fetcher=insane 이어도 폴백용 Bright Data 키 필수". 완료 기준: 주석 존재, 로직 diff 0.
- [ ] 21. [`tests/test_application/`] 라우팅 팩토리 유닛 — (a) `crawler_body_fetcher="insane"` 시
      `_build_body_fetcher()` 가 `FallbackFetcher` 반환 + primary=InsaneFetcher, (b) `"brightdata"` 시
      `BrightDataClient` 반환, (c) SERP 팩토리는 항상 `BrightDataClient`. monkeypatch settings. 완료 기준: 3 케이스 그린.
- [ ] 21b. [`tests/test_crawler/test_page_scraper.py`] **재시도 증폭 상호작용 테스트 추가** — StubFallbackFetcher
      (primary 항상 실패 → fallback) 주입 시 `scrape_pages` 의 1회 batch 재시도가 **폴백 체인 전체를 재실행**함을 검증:
      (a) 지속 실패 URL 1건 → fetch 호출 카운트 = primary 2회(초기 1 + batch 재시도 1) + fallback 2회, (b) batch
      재시도로 성공 회복 시 `InsufficientCollectionError` 미발생. 완료 기준: 호출 카운트 어서션 그린.
- [ ] 22. [`domain/crawler/CLAUDE.md`] **거버넌스 갱신 (PR4 동반 착지)** — §금지 "대체 크롤링 라이브러리 사용 금지"
      라인 갱신(insane 하이브리드 예외 명기) + §핵심규칙 "본문은 HtmlFetcher 추상화 경유, 기본 insane+Bright Data
      폴백" 재서술. **사유: 코드가 본문=insane 으로 동작하는 순간(PR4)부터 문서와 정합해야 함**(과도기 위반 회피).
      완료 기준: 문서와 코드 정합.
- [ ] 23. 🔴 [`SPEC-SEO-TEXT.md`] **거버넌스 갱신 (PR4 동반, 사용자 승인됨)** — §3 [2] + §"기술 스택" + 아키텍처 표
      (본문 수집을 Web Unlocker 로 서술한 라인)을 하이브리드(본문 = insane + Bright Data 폴백)로 갱신. §3 [2] 에
      "본문 fetcher 는 HtmlFetcher 추상화, 기본 insane + Bright Data 폴백" 명기. 완료 기준: SPEC 서술이 코드와 정합.
- [ ] 24. 검증 — `pytest tests/test_application tests/test_crawler --no-cov` + `pyright` 그린.
      완료 기준: 라우팅 유닛 + 재시도 증폭 상호작용 + 기존 흐름 회귀 0.

> PR4 경계: 여기서 처음으로 본문 경로가 insane→brightdata 폴백으로 동작 + 거버넌스 문서(CLAUDE.md/SPEC) 동반 착지.
> `crawler_body_fetcher=brightdata` 로 즉시 롤백 가능(코드 변경 없이 env).

### PR5 — lessons 기록 + 최종 전체 게이트

- [ ] 25. [`tasks/lessons.md`] 결정 기록 — (1) "SERP=BrightData 유지 / 본문=insane 폴백", (2) "insane WAF 가
      네이버 SERP challenge 오판" 실측, (3) "성공 판정은 FetchResult.ok 단일 신호(verdict 열거 금지)", (4) "not_found
      도 폴백 — 낭비 감수 결정", (5) "FallbackFetcher 는 record_usage 미호출(이중집계 차단)". 완료 기준: lessons 섹션 존재.
- [ ] 26. 검증 순서(전체) — ① `ruff check .` 0(vendor 제외) → ② `pyright` 0(domain 의 `from vendor...`
      reportMissingImports 0) → ③ 신규 유닛(`pytest tests/test_crawler tests/test_application --no-cov`) →
      ④ 기존 crawler regression(`pytest tests/test_crawler --no-cov`) 무변경 → ⑤ 실 vendor 1-URL 통합 스모크
      (opt-in) 1회 → ⑥ **Docker 빌드 내 vendor import 스모크 통과**(로컬 경로와 별도) → ⑦
      `bash .claude/hooks/architecture-check.sh` PASS → ⑧ `bash .claude/hooks/build-check.sh`(커버리지 게이트).
      완료 기준: 8개 전부 그린.

## ⚠️ 위험 / 미결 항목 (Risk Register)

- **RI-1 (해소됨 — 벤더 import 그래프 실사 완료)**: insane engine 내부는 **100% 상대 import** 확인 → **rename
  불필요, 내부 무수정**. executor(Playwright) 는 `fetch_chain` 이 **지연 import** 하므로 `enable_playwright=False`
  경로에서 미로드 → executor.py/templates 제외 가능. 서드파티 추가 = curl_cffi + pyyaml 뿐(bs4 보유). step6 에서
  지연 import 및 executor 미로드만 확인.
- **RI-2 (해소됨 — insane 소스 확보)**: insane-search **v0.9.1** 소스 clone 완료(상단 소스 핀 경로). 최소집합
  10 .py + waf_profiles.yaml 실사 확정, 내부 100% 상대 import → 무수정 반입. `curl_cffi` 0.14.0 설치 확인.
  MIT 라이선스 파일 vendor/ 에 동봉.
- **RI-3 (장시간·고동시성 미검증)**: 실측은 단일 IP 120건. 배치 100건+ 동시성 상황의 rate 미검증. → 완화:
  `insane_concurrent_limit=3` 보수적 + FallbackFetcher 가 차단 시 Bright Data 로 흡수. 운영 초기 폴백률을 usage
  (provider 분포)로 모니터링.
- **RI-4 (pyright 통과 관건)**: (1) `HtmlFetcher` Protocol(4종) 도입 후 `BrightDataClient`/`InsaneFetcher`/
  `FallbackFetcher` 가 **4종 전부 구현**해야 구조적 구현체로 인정(`@runtime_checkable` + 시그니처 정합). (2) vendor 는
  pyright include 밖이라 vendor 자체 타입에러는 무관 — **진짜 리스크는 domain 의 `from vendor...` reportMissingImports**
  → `vendor/__init__.py` + packages.find 경로 노출로 해소(step7/9). → 완화: PR1 에서 Protocol pyright 그린 후 어댑터 진행.
- **RI-5 (거버넌스 문서 정합)**: domain/crawler/CLAUDE.md + SPEC-SEO-TEXT.md 가 "본문=Bright Data" 로 서술.
  → **PR4 에서 코드 활성화와 동반**해 두 문서 모두 갱신(사용자 승인 완료). 과도기 위반 회피.
- **RI-6 (폴백 usage 이중 집계 차단)**: → 완화 2중: (1) InsaneFetcher 는 **성공 시에만** insane usage 기록,
  실패(폴백 유도) 시 미기록, (2) **FallbackFetcher 는 record_usage 를 아예 호출하지 않고 logger.warning 만** —
  성공 usage 는 primary/fallback 이 각자 기록. 폴백률은 `provider=brightdata + stage=page_scraping` usage 로 추론.
  테스트로 고정(step14(k), step15(e)).
- **RI-7 (배포 패키징 누락)**: Dockerfile 이 vendor 를 명시 COPY 안 하면 로컬은 통과/배포만 ImportError. editable
  install 은 의존성 레이어의 placeholder 를 요구. → PR2 step8 로 placeholder 선배치 + COPY + Docker 내 import 스모크.
- **RI-8 (mock 이 시그니처 오류를 못 잡음)**: vendor fetch() 시그니처를 mock 하면 오타/실 반환구조 불일치를 유닛이
  통과시킨다. → 완화: PR3 완료 게이트(step16)에 **실 vendor 1-URL 통합 스모크**(opt-in) + 전체 게이트(step26)에
  Docker import 스모크.
- **RI-9 (재시도 증폭 — 유료 폭증)**: `scrape_pages` 의 1회 batch 재시도가 폴백 체인 전체(InsaneFetcher +
  BrightDataClient tenacity 3회)를 재실행 → 지속 실패 URL 1건 worst-case = insane 2회 + brightdata 6회(유료).
  → 완화: InsaneFetcher tenacity 를 **1회로 최소화**(폴백 존재), not_found 조기 폴백 유지. step21b 로 호출 카운트 고정.
- **RI-10 (insane 동시성 no-op 위험)**: `insane_concurrent_limit` 를 정의만 하고 세마포어에 배선하지 않으면
  배치(BATCH_MAX_WORKERS 2~3)가 단일 IP 를 무제한 동시 타격. → 완화: PR3 InsaneFetcher module-level
  `BoundedSemaphore` 실배선(brightdata_client 미러), step14(l) 로 존재 검증.

## 검증 순서 (반복)

```
ruff check .                                  # vendor extend-exclude, 0
pyright                                        # domain 의 from vendor... reportMissingImports 0
pytest tests/test_crawler --no-cov            # 어댑터 + verdict 분기 + 재시도 증폭 + 기존 regression
pytest tests/test_application --no-cov         # 라우팅 팩토리 + 단일 흐름 회귀
python -c "import vendor.insane_search"        # 로컬 import 스모크
# (opt-in) 실 vendor 1-URL 통합 스모크 + Docker 빌드 내 import 스모크
bash .claude/hooks/architecture-check.sh       # domain/crawler → vendor 는 미검사, PASS 확인
bash .claude/hooks/build-check.sh              # 최종 커버리지 게이트 (한 번만)
```

## PR 분할 요약

1. **PR1** HtmlFetcher Protocol(4종) + 타입 완화 (동작 무변경, 순수 리팩터)
2. **PR2** insane v0.9.1 벤더링(10 .py + yaml, executor/templates 제외) + 패키징/Docker placeholder/린트 배선 (런타임 미연결)
3. **PR3** InsaneFetcher(ok 판정 + suspect_ok sanity + 세마포어 + tenacity 1) + FallbackFetcher(무 record_usage) 어댑터 + 유닛 + 🔴 실 vendor 1-URL 통합 스모크 게이트 (라우팅 미연결)
4. **PR4** settings 토글 + stage_runner 본문 팩토리 분기 + **거버넌스 문서(CLAUDE.md/SPEC) 동반 착지** (폴백 활성, env 즉시 롤백)
5. **PR5** lessons 기록 + 최종 전체 게이트(Docker import 스모크 포함)

---

# SERP insane 하이브리드 확장 — 2026-07-06 계획

목표: 본문(page_scraper)에 이미 착지한 insane(curl_cffi) 우선 + Bright Data 폴백 하이브리드를
**SERP 3종(통합검색/블로그탭 = 분석 트랙, 난이도 SERP, 순위추적 cron)** 으로 확장해 Bright Data
(유료 Web Unlocker) 호출을 추가로 절감한다. 무손실 원칙(selector 부정합 = 자동 폴백) 유지.

SPEC 참조: §3 [1] (SERP 수집). 본문 하이브리드 = 위 "insane-search 하이브리드 fetcher 통합" 섹션(완료).

## 배경 — 완료된 것 (본문 하이브리드, main 커밋)

- `domain/crawler/fetcher.py` `HtmlFetcher` Protocol (fetch/close/`__enter__`/`__exit__` 4종).
- `vendor/insane_search/` 벤더링(curl-only, v0.9.1).
- `domain/crawler/insane_fetcher.py` `InsaneFetcher` — 성공판정=`FetchResult.ok`(+suspect_ok sanity),
  module-level `BoundedSemaphore(settings.insane_concurrent_limit)`, `close=POOL.reset`.
  **현재 본문 전용 하드코딩**: `_call_vendor` 가 `device_class="mobile", enable_playwright=False,
  enable_learning=False, enable_phase0=True, max_attempts=_VENDOR_MAX_ATTEMPTS(3)`, **success_selectors 없음**.
- `domain/crawler/fallback_fetcher.py` `FallbackFetcher(primary, fallback)` — 폴백 시 record_usage 미호출.
- `application/stage_runner.py` `_build_body_fetcher()` + `run_stage_page_scraping` 라우팅.
  settings `crawler_body_fetcher`(default insane), `insane_concurrent_limit=3`, `insane_timeout_seconds=30`.
- `application/usage_tracker.py::estimate_cost` 에 `provider=="insane"` → 0.0 분기 이미 존재(재사용).

## 배경 — 이번 확장의 실측 근거 (확정)

- SERP(통합검색/블로그탭/난이도)를 insane 으로 fetch 시 **`success_selectors=["#main_pack"]`** 주면
  verdict `challenge`(executed_attempts=9, grid 소진) → **`strong_ok`(executed_attempts=1)** 로 완전 우회.
  `#main_pack` 이 3종 SERP 공통 안정 컨테이너(각 정확히 1개 존재).
- 우회분 HTML 파서 결과가 Bright Data 와 일치: `_parse_serp_html` 블로그 URL 6/6 완전 일치,
  `parse_serp`(난이도) SerpComposition 은 광고 카드 수(요청시점 변동)만 ±3 차이·SEO 의미 섹션 동일.
- 단일 IP SERP **30건 연속 무차단**(strong_ok 30/30, 세션 누적 ~148 요청). **단 30건 상한까지만 측정 —
  그 이상 임계 미측정**.
- challenge 는 실제 차단 아님(status 200, `soft:captcha` 오탐). **정확한 selector 가 관건** — 존재 안 하는
  selector 주면 정상 HTML 도 challenge 강등. 즉 selector 틀려도 `not result.ok` → 폴백(무손실)이라 안전.

## 🔴 확정 설계 결정 (이 계획은 이걸 따른다)

> **D1. InsaneFetcher 파라미터화 — 본문 default 무변경**
> - 현재 `_call_vendor` 의 본문 전용 하드코딩을 생성자 파라미터로 승격:
>   `InsaneFetcher(*, device_class="mobile", success_selectors: list[str] | None = None,
>   enable_phase0: bool = True, max_attempts: int = _VENDOR_MAX_ATTEMPTS)`.
> - `enable_playwright=False`(거버넌스상 Playwright 영구 금지), `enable_learning=False` 는 **파라미터화하지
>   않고 하드코딩 유지**(파라미터 표면 최소화, YAGNI).
> - `_call_vendor` 를 `@staticmethod` → **인스턴스 메서드**로 전환(self 설정 읽기). `vendor_fetch(...,
>   device_class=self._device_class, success_selectors=self._success_selectors, enable_phase0=self._enable_phase0,
>   max_attempts=self._max_attempts, ...)`.
> - 기존 본문 호출 `InsaneFetcher()` = default(mobile, selectors=None, phase0=True, max=3) → **동작·kwargs 무변경**.
>   기존 유닛(`tests/test_crawler/test_insane_fetcher.py:79` 가 `device_class=="mobile"` 어서션)이 회귀 가드.
> - SERP 용 인스턴스: `InsaneFetcher(device_class="desktop", success_selectors=["#main_pack"])`.
>
> **D2. SERP 팩토리 — `build_serp_fetcher()` (stage_runner)**
> - `application/stage_runner.py` 에 팩토리 신규. `settings.crawler_serp_fetcher == "insane"` 이면
>   `FallbackFetcher(InsaneFetcher(device_class="desktop", success_selectors=[_SERP_SUCCESS_SELECTOR]),
>   _build_brightdata_client())`, 그 외 `_build_brightdata_client()`.
> - `#main_pack` 은 상수 승격 → `_SERP_SUCCESS_SELECTOR = "#main_pack"` (매직 문자열 금지 규칙).
> - **명명 결정**: 본문 팩토리 `_build_body_fetcher` 는 stage_runner 내부 전용이라 private. SERP 팩토리는
>   `keyword_difficulty_orchestrator` / `ranking_orchestrator` 가 **cross-import** 하므로 **public
>   `build_serp_fetcher`** 로 노출(application↔application import 는 application/CLAUDE.md 상 허용, 두 orchestrator
>   가 이미 `from application.usage_tracker import ...` 하는 선례와 정합). 토글 매직 문자열은 기존
>   `_BODY_FETCHER_INSANE/_BODY_FETCHER_BRIGHTDATA` 재사용.
>
> **D3. 라우팅 대상 3종 — PR 분리**
> - 분석 트랙: `run_stage_serp_collection`(collect_serp) + `keyword_difficulty_orchestrator._build_client`(난이도).
> - 순위추적: `ranking_orchestrator.check_rankings_for_publication` 의 `BrightDataClient` 직접 인스턴스화.
>
> **D4. settings 토글 + 롤백 밸브 (권고는 아래 별도 절)**
> - 분석 트랙: `crawler_serp_fetcher`(env `CRAWLER_SERP_FETCHER`). 롤백 밸브 필수(env 로 즉시 brightdata 강제).
> - 순위추적: 위험 비대칭(매일 cron 대량, 30건까지만 실측) 때문에 **분리 토글 `ranking_serp_fetcher`** 권고
>   (default 보수). 아래 "default 토글 권고" 참조.
>
> **D5. 성공판정/폴백 — 기존 로직 100% 재사용**
> - success_selectors 부정합으로 challenge → `not result.ok` → `InsaneFetchError`(BrightDataTransientError 하위)
>   → `FallbackFetcher` 가 Bright Data 로 폴백(무손실). content sanity 마커(`captcha` 등)는 본문과 공유하나
>   실측상 정상 SERP HTML 은 `_content_is_sane` 통과(strong_ok + 파서 일치 확인). insane 성공 시
>   `record_usage(provider="insane", cost=0)` → difficulty/ranking 의 `collect_usage`+`save_usage_to_supabase`
>   가 stage 별로 수확 → 폴백률 telemetry 확보.

## 변경 대상 파일

| 파일 | 현재 | 변경 |
|---|---|---|
| `domain/crawler/insane_fetcher.py` | `_call_vendor` staticmethod, 본문 하드코딩 | `__init__` 4파라미터 + `_call_vendor` 인스턴스화, default 무변경 |
| `application/stage_runner.py` | `_build_body_fetcher`, `run_stage_serp_collection(client: BrightDataClient|None)` | `build_serp_fetcher()` + `_SERP_SUCCESS_SELECTOR` 상수, serp 라우팅, client 타입 `HtmlFetcher|None` 완화 |
| `application/keyword_difficulty_orchestrator.py` | `_build_client()→BrightDataClient` | `build_serp_fetcher()` 사용, `analyze_keyword(client: HtmlFetcher|None)` 완화 |
| `application/ranking_orchestrator.py` | `check_rankings_for_publication` 이 `BrightDataClient(...)` 직접 | `build_serp_fetcher()` 사용(close 위임 유지) |
| `config/settings.py` | `crawler_body_fetcher` 등 | `crawler_serp_fetcher`(PR2) + `ranking_serp_fetcher`(PR3) 필드 + 주석 갱신 |
| `config/.env.example` | insane 토글 3필드 | serp 토글 필드 예시 동기화 |
| `domain/crawler/CLAUDE.md` | "SERP·keyword_difficulty·ranking 은 여전히 Bright Data 단독" | 하이브리드 반영(PR별 부분 갱신) |
| `SPEC-SEO-TEXT.md §3 [1]` | SERP=Web Unlocker 서술 | 하이브리드 서술 — **🔴 사용자 승인 필요**(아래 참조) |
| `tests/test_crawler/test_insane_fetcher.py` | 본문 default 유닛 | 파라미터 전달 유닛 추가 |
| `tests/test_application/` | 본문 팩토리 유닛 | SERP 팩토리 라우팅 유닛 추가 |

### 선행 조건
- [ ] 위 "insane-search 하이브리드 fetcher 통합"(본문) 5개 PR 모두 main 착지 (자산 존재 확인 — 완료됨)
- [ ] `_SERP_SUCCESS_SELECTOR="#main_pack"` 가 통합검색/블로그탭/난이도 3종에서 각 1개 존재 재확인(실측 완료, 착수 시 1회 재검)

---

## PR-S1 — InsaneFetcher 파라미터화 (순수 리팩터, 라우팅 미연결)

> 경계: 생성자 파라미터 승격만. 본문 default 무변경. SERP 아직 아무도 호출 안 함. 리뷰 최소화 목적 분리.

- [ ] 1. [`domain/crawler/insane_fetcher.py`] `__init__(self, *, device_class="mobile",
      success_selectors=None, enable_phase0=True, max_attempts=_VENDOR_MAX_ATTEMPTS)` 추가 → self 필드 저장
      (타입힌트 `list[str] | None`). — 검증: `InsaneFetcher()` 기본값이 기존 하드코딩과 동일.
- [ ] 2. [`insane_fetcher.py`] `_call_vendor` `@staticmethod` → 인스턴스 메서드. `vendor_fetch(url,
      device_class=self._device_class, success_selectors=self._success_selectors, enable_playwright=False,
      enable_learning=False, enable_phase0=self._enable_phase0, max_attempts=self._max_attempts,
      timeout=settings.insane_timeout_seconds)`. `_fetch_with_retry` 의 `self._call_vendor(url)` 유지. —
      검증: `enable_playwright/enable_learning` 여전히 하드코딩 False.
- [ ] 3. [`tests/test_crawler/test_insane_fetcher.py`] 유닛 추가 — (a) `InsaneFetcher()` → kwargs
      `device_class=="mobile" & success_selectors is None`(기존 79행 어서션 유지·확장), (b)
      `InsaneFetcher(device_class="desktop", success_selectors=["#main_pack"])` → kwargs 전파 어서션,
      (c) `max_attempts`/`enable_phase0` 커스텀 전파. — 검증: `pytest tests/test_crawler/test_insane_fetcher.py --no-cov` green.
- [ ] 4. 회귀 — `pytest tests/test_crawler --no-cov`(fallback/page_scraper/smoke 무변경) + `ruff check .` +
      `pyright` 0. — 검증: 파일 300줄/함수 30줄 이내 유지(현 134줄 → +약 15줄).

---

## PR-S2 — SERP 팩토리 + 분석 트랙 라우팅 (통합검색/블로그탭 + 난이도)

> 경계: 여기서 처음 분석 트랙 SERP 가 insane→brightdata 폴백으로 동작. ranking 은 아직 Bright Data.

- [ ] 5. [`config/settings.py`] `crawler_serp_fetcher: str = Field(default=?, ...)` 추가(default 는 아래 권고절
      확정 후). env `CRAWLER_SERP_FETCHER`. 주석: "분석 트랙 SERP(통합검색/블로그탭) + 난이도 SERP 라우팅.
      'insane'=하이브리드 폴백, 'brightdata'=강제 단독(롤백 밸브). ranking 은 별도 `ranking_serp_fetcher`." —
      검증: `settings.crawler_serp_fetcher` 로드.
- [ ] 6. [`config/settings.py`] 기존 `crawler_body_fetcher` 주석의 "SERP 수집·keyword_difficulty·ranking 은
      값과 무관하게 항상 Bright Data 다" 문구 갱신 — "SERP·난이도는 `crawler_serp_fetcher`, ranking 은
      `ranking_serp_fetcher` 로 별도 라우팅" 로 정정. `bright_data_web_unlocker_zone` 설명 유지(SERP 폴백 공용). —
      검증: 주석이 코드와 정합.
- [ ] 7. [`config/.env.example`] `CRAWLER_SERP_FETCHER` 예시 추가(동기화). — 검증: 키 존재.
- [ ] 8. [`application/stage_runner.py`] `_SERP_SUCCESS_SELECTOR = "#main_pack"` 상수 + `build_serp_fetcher()
      -> HtmlFetcher` 신규 — 토글 insane 시 `FallbackFetcher(InsaneFetcher(device_class="desktop",
      success_selectors=[_SERP_SUCCESS_SELECTOR]), _build_brightdata_client())`, 그 외 `_build_brightdata_client()`.
      insane import 는 브랜치 내 지연 로드(brightdata 강제 시 vendor 미로드, `_build_body_fetcher` 패턴 미러). —
      검증: 함수 30줄 이내, public(cross-import 대상).
- [ ] 9. [`stage_runner.py`] `run_stage_serp_collection` — `client: BrightDataClient | None` →
      `HtmlFetcher | None` 타입 완화, 기본 생성 `_build_brightdata_client()` → `build_serp_fetcher()`.
      `collect_serp(keyword, client)` 는 이미 HtmlFetcher 계약 → 무변경. owned_client close 로직 유지
      (FallbackFetcher.close 가 양쪽 위임). — 검증: 기존 테스트의 fake client 주입 무영향(구조적 타이핑).
- [ ] 10. [`application/keyword_difficulty_orchestrator.py`] `_build_client()` 반환을 `build_serp_fetcher()`
      로 교체(반환 타입 `HtmlFetcher`). `analyze_keyword(client: BrightDataClient | None)` →
      `HtmlFetcher | None` 완화. `batch_analyze_keywords` 의 `cli=_build_client()` 재사용 경로 무변경
      (동일 인스턴스 12 worker 공유 → insane module-level 세마포어가 동시성 3 으로 게이트, 아래 위험 참조). —
      검증: `cli.fetch(url)`(ThreadPool `run_in_isolated_usage_ctx`) 계약 유지, SERP 캐시(`get_cached`) 경로 무변경.
- [ ] 11. [`tests/test_application/`] SERP 팩토리 라우팅 유닛 — (a) `crawler_serp_fetcher="insane"` →
      `FallbackFetcher`(primary=InsaneFetcher desktop+`#main_pack`, fallback=BrightDataClient), (b) `"brightdata"` →
      `BrightDataClient`, (c) insane 인스턴스의 device_class/success_selectors 어서션. — 검증:
      `pytest tests/test_application --no-cov` green.
- [ ] 12. [`domain/crawler/CLAUDE.md`] 규칙1 "SERP·keyword_difficulty·ranking 은 여전히 Bright Data 단독" →
      "SERP(통합검색/블로그탭)·keyword_difficulty 는 `crawler_serp_fetcher` 하이브리드(기본 insane+Bright Data
      폴백), ranking 은 별도 토글" 로 갱신. `serp_collector.py` 파일 책임의 "(Bright Data 유지)" 문구 정정.
      금지 절 "SERP/ranking/keyword_difficulty 는 Bright Data" 재서술(ranking 만 잔여). — 검증: 문서가 코드와 정합.
- [ ] 13. 회귀 — `pytest tests/test_crawler tests/test_application --no-cov` + `ruff check .` + `pyright` 0 +
      `bash .claude/hooks/architecture-check.sh`(domain→vendor 미검사 PASS). — 검증: 단일 흐름/난이도 회귀 무변경.

> 🔴 SPEC 갱신(§3 [1]): 분석 트랙 SERP 가 코드상 하이브리드로 동작하는 순간 SPEC 서술과 과도기 불일치가
> 생긴다. **본문 트랙 PR4 가 §3 [2] 를 "사용자 승인됨"으로 갱신한 선례** 존재. 본 PR 도 §3 [1] SERP 수집 서술을
> "SERP fetcher 는 HtmlFetcher 추상화, 기본 insane + Bright Data 폴백(`success_selectors=["#main_pack"]`)" 로
> 갱신해야 정합. **planner 는 SPEC 을 단독 수정하지 않는다 — 사용자 승인 후 step 으로 편입**(→ 아래 "결정 필요").

---

## PR-S3 — 순위추적 cron 라우팅 (신중, 위험 비대칭)

> 경계: ranking 은 매일 cron 대량 호출 → 비용 절감 효과 최대, 단일 IP 대량 위험도 최대. 실측 30건 상한.
> **분석 트랙(PR-S2) 운영 관측 후 착수** 권고.

- [ ] 14. [🟡 선행 실측] ranking 대량 적용 전 **더 높은 부하 임계 확인** — 단일 IP 로 `build_main_search_url`
      SERP 를 100+ 연속 fetch 스모크(scratchpad 스크립트)로 strong_ok 유지·차단 신호 부재 확인. 30→100+ 확장
      실측 없이 ranking insane 기본 활성 금지. — 검증: 연속 100건 strong_ok 로그 + 차단 마커 0.
- [ ] 15. [`config/settings.py`] `ranking_serp_fetcher: str = Field(default="brightdata", ...)` 추가(env
      `RANKING_SERP_FETCHER`). 주석: "순위추적 cron SERP 라우팅. 매일 대량 호출 위험으로 default 보수
      (brightdata). step14 부하 실측 통과 후 env 로 insane 전환." — 검증: 로드 + default brightdata.
- [ ] 16. [`application/ranking_orchestrator.py`] `check_rankings_for_publication` 의 `BrightDataClient(api_key=,
      zone=)` 직접 인스턴스화(437행)를 `from application.stage_runner import build_serp_fetcher` →
      `build_serp_fetcher(settings.ranking_serp_fetcher)` 로 교체(팩토리에 토글 인자 오버로드 or 전용 분기).
      **ranking 도메인 격리 유지**: ranking_orchestrator(application)만 팩토리 참조, `domain/ranking` 은 무변경.
      `reset_usage`/`collect_usage`/`client.close()` finally 블록 유지(FallbackFetcher.close 양쪽 위임). —
      검증: `check_rankings_for_publication` usage 수확·top10·진단·visibility 재산출 경로 무변경.
- [ ] 17. [`build_serp_fetcher`] 시그니처 확장 — `build_serp_fetcher(mode: str | None = None)`, None 이면
      `settings.crawler_serp_fetcher`. ranking 은 `settings.ranking_serp_fetcher` 명시 주입. (분석/ranking 이
      단일 팩토리·상이 토글 공유하되 매직 문자열 판정은 동일 `_BODY_FETCHER_*` 재사용.) — 검증: 두 토글 독립 동작.
- [ ] 18. [`tests/test_application/`] ranking 라우팅 유닛 — `ranking_serp_fetcher` insane/brightdata 분기 +
      `check_rankings_for_publication` 이 팩토리 경유(BrightDataClient 직접 인스턴스화 부재) 어서션(monkeypatch). —
      검증: `pytest tests/test_application --no-cov` green.
- [ ] 19. [`domain/crawler/CLAUDE.md`] ranking 잔여 문구 최종 갱신 — "ranking 도 `ranking_serp_fetcher`
      하이브리드(default 보수 brightdata)". PR-S2 에서 남긴 "ranking 만 잔여" 해소. — 검증: 문서 정합.
- [ ] 20. 회귀 — `pytest tests/test_application tests/test_ranking --no-cov` + `ruff check .` + `pyright` 0. —
      검증: ranking 격리(DI) 위반 0, 단일 흐름 무변경.

---

## PR-S4 — lessons 기록 + 최종 게이트

- [ ] 21. [`tasks/lessons.md`] 결정 기록 — (1) "SERP 3종 insane 우회 관건 = `success_selectors=['#main_pack']`
      (부정합 selector 는 정상 HTML 도 challenge 강등 → 폴백)", (2) "분석 SERP 30건 무차단 실측·ranking 은
      100+ 실측 후 전환", (3) "insane module-level 세마포어(3)가 difficulty batch parallel(12)을 3 동시로 게이트". —
      검증: lessons 항목 존재.
- [ ] 22. 최종 — `bash .claude/hooks/build-check.sh`(커버리지 게이트 한 번). — 검증: 전체 green.

---

## 🔴 default 토글 권고 (사용자 결정 필요)

실측이 강하나(분석 SERP 30/30 무차단 + 파서 일치) **ranking 대량 임계는 30건까지만** 측정됨. 위험 비대칭
(분석=on-demand 소량 / ranking=매일 cron 대량)을 반영해 **트랙별 상이 default** 를 권고한다.

| 토글 | 대상 | 권고 default | 사유 |
|---|---|---|---|
| `crawler_serp_fetcher` | 분석 SERP + 난이도 | **`insane`(공격적)** | on-demand·소량, 실측 강함(6/6 URL 일치·30/30 무차단), 롤백=env 즉시 |
| `ranking_serp_fetcher` | 순위추적 cron | **`brightdata`(보수)** | 매일 대량, 30건 초과 임계 미측정. step14 100+ 실측 통과 후 env 로 insane 전환 |

- **대안(더 보수)**: 단일 토글 `crawler_serp_fetcher` default `brightdata` + 관측 후 일괄 flip. 장점=표면 최소,
  단점=분석 트랙의 강한 실측 근거를 초기부터 활용 못 함. → 두 토글안(권고)이 위험 대비 이득 균형이 낫다고 판단.
- **어느 안이든 롤백 밸브(env 즉시 brightdata 강제) 필수** — 코드 변경 0 으로 되돌린다.

## ⚠️ 위험 요소 (Risk Register — SERP 확장)

- **RS-1 (ranking 대량 단일 IP, 최고 위험)**: 매일 cron 이 전 publication SERP 를 단일 IP insane 으로 대량
  fetch → 30건 초과 임계 미측정. → 완화: `ranking_serp_fetcher` default `brightdata` + step14 100+ 실측 게이트 +
  실측 통과 후에만 env 전환. selector 부정합/차단 시 자동 Bright Data 폴백(무손실).
- **RS-2 (difficulty batch 동시성 캡)**: `keyword_difficulty_batch_parallel=12` worker 가 단일 insane
  module-level 세마포어(`insane_concurrent_limit=3`)를 공유 → 실효 동시성 3 으로 게이트, batch 처리량 저하 가능.
  → 완화(권고): **저하 수용 + 관측**(단일 IP 보호 관점에선 오히려 안전). 필요 시 `insane_concurrent_limit`
  신중 상향 or difficulty 만 brightdata 유지. 선행 최적화 금지(YAGNI).
- **RS-3 (selector 부정합 → 100% 폴백)**: `#main_pack` 이 네이버 UI 개편으로 사라지면 전 SERP 가 challenge →
  전량 Bright Data 폴백(비용 원복, 무손실·무장애). → 완화: 폴백률을 `provider=insane vs brightdata + stage`
  usage 분포로 상시 관측. 급증 시 selector 재확인. 착수 시 3종 selector 1회 재검(선행 조건).
- **RS-4 (content sanity 오탐)**: SERP HTML 이 block 마커(`captcha` 등) 리터럴 포함 시 `_content_is_sane`
  거절 → 과도 폴백(안전하나 유료). → 실측상 정상 SERP 는 strong_ok+파서 일치로 통과 확인. 데스크톱 SERP 도
  동일 경로 실측됨. 잔여 위험 낮음, 폴백률 관측으로 커버.
- **RS-5 (SPEC 과도기 불일치)**: 분석 SERP 가 코드상 하이브리드로 도는 순간 SPEC §3 [1] 서술과 불일치. →
  완화: PR-S2 에 SPEC 갱신 step 편입(단 **사용자 승인 후**). 본문 트랙 §3 [2] 선례 준수.
- **RS-6 (cross-import 명명)**: `build_serp_fetcher` 를 difficulty/ranking orchestrator 가 stage_runner 에서
  import → application↔application 허용이나 stage_runner 가 의존 허브화. → 완화: public 함수로 명시 노출(private
  `_` 아님). 리뷰어가 선호 시 `application/serp_fetcher_factory.py` 분리 가능(1-함수라 기본은 stage_runner 유지).

## 🔴 결정 필요 (착수 전 사용자 확인)

1. **default 토글** — 위 권고표(분석=insane / ranking=brightdata) 채택 vs 단일 토글 보수안?
2. **SPEC §3 [1] 갱신** — planner 는 SPEC 단독 수정 불가. 본문 §3 [2] 선례대로 이번에도 갱신 승인?
3. **PR-S3 착수 시점** — 분석 트랙(PR-S2) 운영 관측(폴백률·차단신호) N일 후 vs 즉시?

## 검증 순서 (반복)

```
pytest tests/test_crawler/test_insane_fetcher.py --no-cov   # 파라미터 전파 + default 무변경
pytest tests/test_crawler --no-cov                          # fallback/page_scraper/serp 회귀
pytest tests/test_application --no-cov                       # SERP/ranking 팩토리 라우팅 + 단일 흐름 회귀
pytest tests/test_ranking --no-cov                           # ranking 격리·측정 경로 회귀 (PR-S3)
ruff check . && pyright                                       # 린트/타입 0
bash .claude/hooks/architecture-check.sh                      # domain→vendor 미검사 PASS
bash .claude/hooks/build-check.sh                             # 최종 커버리지 게이트 (한 번만)
```

## PR 분할 요약 (SERP 확장)

1. **PR-S1** InsaneFetcher 파라미터화(4파라미터, default 무변경) + 유닛 (순수 리팩터, 라우팅 미연결)
2. **PR-S2** `build_serp_fetcher()` + `#main_pack` 상수 + `crawler_serp_fetcher` 토글 + 분석 SERP·난이도 라우팅
   + 거버넌스(crawler CLAUDE.md) + 🔴 SPEC §3 [1] 갱신(승인 후) + 유닛
3. **PR-S3** ranking 라우팅 + `ranking_serp_fetcher`(default 보수) + 🟡 100+ 부하 실측 게이트 + 격리 유지 + 유닛
4. **PR-S4** lessons 기록 + 최종 전체 게이트
