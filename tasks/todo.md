# Contents Creator — Todo

> 현재: Phase 0 부트스트랩 완료 → Phase 0.5 SEO 실측 완료 → **Phase 0.6 브랜드 카드 실측 블로킹**
>
> 두 트랙 병행: SEO (기존 Phase 1~7) + 브랜드 카드 (신규 Phase B1~B9). 합류 use case = `run_full_package`.

## ✅ 완료

- [x] v1 프로젝트 초기화 — 2026-04-15
- [x] SPEC-SEO-TEXT.md v2 작성 — 2026-04-15
- [x] 블로그 해시태그 분석 반영 — 2026-04-15
- [x] 2차 비평 반영 (C1 iframe 실측, M1 fixer, M2 차별화 N<10, M3 schema_version, M4 태그 클램프 제거, M5 outline.md) — 2026-04-15
- [x] Harness 구성 (5 skills + 5 agents + 2 hooks + settings.json) — 2026-04-15
- [x] CLAUDE.md (루트 + 5 도메인) — 2026-04-15
- [x] Phase 2 Next.js 대비 application 레이어 설계 — 2026-04-15
- [x] 프로젝트 스캐폴딩 (pyproject, .gitignore, config, application, scripts, 도메인 패키지) — 2026-04-15
- [x] **SPEC-BRAND-CARD.md v1 작성 + 4차 재검토 완료** — 2026-04-16 (1094줄, 16개 섹션)
- [x] **하네스 재정렬 (SPEC-SEO-TEXT 리네임 + CompliancePolicy 도입 반영)** — 2026-04-16
- [x] **pyproject 에 브랜드 카드 트랙 의존성 추가** (playwright/jinja2/python-docx/pypdf/pdfplumber/pillow) — 2026-04-16
- [x] **schema.sql v3 — brand_profiles/brand_assets/brand_media_assets/brand_cards 4개 테이블 추가** — 2026-04-16
- [x] **plan-reviewer 교차 검토 (SPEC-SEO-TEXT + SPEC-BRAND-CARD + todo 3자)** — 2026-04-16. Critical 3건 → 본 todo 재작성으로 해결

## 🧪 Phase 0.5 — SEO 트랙 착수 전 실측 (블로킹)

### [Pre-1] 개발 환경 준비 ✅ 완료 (2026-04-29)
- [x] `python -m venv .venv` 후 활성화 (기존 venv 재사용) — 2026-04-16
- [x] `pip install -e ".[dev]"` 실행 성공 확인 — 신규 의존성 6종(playwright/jinja2/python-docx/pypdf/pdfplumber/pillow) 포함 — 2026-04-16
- [x] `bash .claude/hooks/build-check.sh` 그린 확인 — 874 passed, coverage 75.65% (`web` extra 동반 설치 후) — 2026-04-29
- [x] Supabase 프로젝트 생성 + `config/schema.sql` v3 적용 — 13개 테이블 전부 적용 확인 (pattern_cards/generated_contents/brand_profiles/brand_assets/brand_media_assets/brand_cards/api_usage/publications/ranking_snapshots/serp_top10_snapshots/visibility_diagnoses/republish_jobs/publication_actions) — 2026-04-29

### [B3] 네이버 스마트에디터 HTML 호환성 실측 ✅ 완료 (2026-04-15)
- [x] 샘플 HTML 생성 (`dev/active/naver-compat-test.html`) — 화이트리스트 모든 태그 + Q&A + 통계 포함
- [x] 브라우저 렌더링 → 네이버 스마트에디터 ONE 붙여넣기 테스트
- [x] 화이트리스트 모든 태그 보존 확인 (h2, h3, p, strong, em, hr, ul, ol, li, blockquote, table, thead, tbody, tr, th, td)
- [x] **중첩 ul/ol 은 네이버 에디터가 평탄화/소실시킴** — 생성 단계에서 중첩 금지 규칙 추가
- [x] `SPEC-SEO-TEXT.md` §3 [9], `generation` 스킬, `composer/CLAUDE.md` 에 중첩 리스트 차단 규칙 반영
- [x] `tasks/lessons.md` B3 섹션에 결과 기록

### [C1] Bright Data Web Unlocker iframe 실측 ✅ 완료 (2026-04-15)
- [x] Bright Data 가입 + API 키 발급
- [x] Web Unlocker zone 생성 (`naver_web_unlockers`, Korea, JS rendering ON)
- [x] `config/.env` 에 `BRIGHT_DATA_API_KEY`, `BRIGHT_DATA_WEB_UNLOCKER_ZONE` 반영
- [x] 네이버 검색 페이지 fetch 검증 — SERP 정상 반환 (871KB, 207회 `blog.naver.com` 매칭)
- [x] 블로그 포스트 URL 실측 — **모바일 `m.blog.naver.com` 은 단일 호출로 본문 OK** (130KB, `se-main-container` 등 본문 컨테이너 모두 존재), 데스크톱 `blog.naver.com` 은 iframe 껍데기(3KB)만 반환
- [x] **결정: `page_scraper.py` 는 URL 을 `m.blog.naver.com` 으로 정규화 후 단일 호출**. 2단계 호출 불필요
- [x] URL 필터 정규식 확정: `https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}` (`/clip/` 배제)
- [x] `tasks/lessons.md` C1 섹션에 실측 데이터 기록
- [x] `SPEC-SEO-TEXT.md` §3 [2] 및 crawling 스킬 업데이트

### [C3] Claude Code 훅 환경 변수 실측 ✅ 완료 (2026-04-15)
- [x] Claude Code 훅은 JSON 을 **stdin** 으로 전달 (환경 변수 아님) — claude-code-guide 확인
- [x] `post-edit-lint.sh` 가 Python 으로 stdin JSON 파싱하도록 수정 (`.tool_input.file_path`)
- [x] `settings.json` command 필드에서 `$CLAUDE_FILE_PATH` 제거, `bash .claude/hooks/post-edit-lint.sh` 로 단순화
- [x] 진단 로그 `dev/active/hook-debug.log` 추가 + `.gitignore` 에 등록
- [x] 4개 파일 Edit 테스트 → 로그에 절대 경로 정상 기록 확인
- [ ] _선택_: `domain/generation/body_writer.py` 에 일부러 `intro_text` 추가해 R1 차단 실증 (파일 존재 안 해서 Phase 1 진입 시 겸사겸사 확인)

### [Pre-2] 환경 변수 전체 완결 ✅ 완료 (2026-04-16)
- [x] `config/.env` 에 다음 키 모두 채움:
  - `BRIGHT_DATA_API_KEY`, `BRIGHT_DATA_WEB_UNLOCKER_ZONE`
  - `ANTHROPIC_API_KEY`
  - `GEMINI_API_KEY` (Google AI Studio, Gemini 3.1 Flash Image + Nano Banana)
  - `SUPABASE_URL`, `SUPABASE_KEY`
- [x] `python -c "from config.settings import settings; print(settings.bright_data_api_key is not None)"` 로 로드 확인 — bright_data/anthropic/gemini/supabase_url/supabase_key 5종 모두 True — 2026-04-29

---

## 🎨 Phase 0.6 — 브랜드 카드 착수 전 실측 (블로킹)

> SPEC-BRAND-CARD.md §15-2 실측 체크리스트. SEO 트랙 `[B3]` 와 네임스페이스 충돌 방지를 위해 **`[BC-*]` 접두사** 사용.

### [BC-1] Playwright 설치 + Chromium headless 렌더 실측 ✅ 완료 (2026-04-16)
- [x] `playwright install chromium` — Windows `~/AppData/Local/ms-playwright/chromium-1208/` 정상 설치
- [x] 샘플 HTML (`dev/active/bc-tests/bc1-sample.html`) 작성 — 1080 가로, 4 블록
- [x] `page.goto(file://)` → `page.screenshot(full_page=True)` 정상 동작
- [x] 출력 PNG 1080×1601, `body.scrollHeight === png.height` 일치
- [x] `tasks/lessons.md` BC-1 섹션 기록

### [BC-2] 한국어 웹폰트 임베딩 (Pretendard) ✅ 완료 (2026-04-16)
- [x] Pretendard Variable woff2 2MB 다운로드 (jsdelivr `orioncactus/pretendard@v1.3.9`, OFL) → `assets/fonts/Pretendard-Regular.woff2`
- [x] `@font-face` 임베딩 + Playwright 렌더
- [x] `document.fonts.size === 1`, `getComputedStyle fontFamily === Pretendard` 확인
- [x] 한글 렌더 깨짐 0건 (히어로 72px + 본문 22px + 카드 24px 혼합)
- [x] `tasks/lessons.md` BC-2 섹션 기록

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

### [BC-5] 로고 자동 추출 셀렉터 세트 실측 ✅ 완료 (2026-04-29)
- [x] 로컬 fixture 7/7 통과 (`dev/active/bc-tests/bc5_logo.py`)
- [x] 폴백 셀렉터 5단 순서 확정: `link[rel=icon]` → `meta[og:image]` → `header img[alt*=logo]` → `[class*=logo] img` → `img[src*=logo]`
- [x] 우선순위 정확 (case6 link + og:image 공존 → link 선택)
- [x] 실존 한의원 홈페이지 **7곳 실측 7/7 성공** (daeatdiet 5지점 + serea + liting). 모두 1단 `link[rel=apple-touch-icon]` 매칭. lessons.md BC-5 Phase 2 표 기록 — 2026-04-29
- [x] `tasks/lessons.md` BC-5 섹션 기록

### [BC-6] Gemini Nano Banana 이미지 생성 실측 ✅ 완료 (2026-04-16)
- [x] `google-genai==1.73.1` SDK 로 1회 호출 성공
- [x] 모델명 확정: `gemini-2.5-flash-image` (정식 이름, preview 없음)
- [x] 응답시간 9.27초, 1.15MB PNG, `finish_reason=STOP`
- [x] 이미지 품질 확인: 프롬프트 지시(beige/forest green, flat, no text) 정확 반영
- [x] SHA256 캐시 키 일관성 확인
- [x] 경고 기록: `GOOGLE_API_KEY` 가 `GEMINI_API_KEY` 보다 우선 (SDK 동작)
- [ ] **추후**: 의료 키워드 5종 safety filter 차단율 별도 스트레스 테스트 (이번 실측은 안전 프롬프트만)
- [x] `tasks/lessons.md` BC-6 섹션 기록

### [BC-7] Playwright 분할 로직 현실성 점검 ✅ 완료 (2026-04-16)
- [x] 10400px HTML 샘플 (`bc7-long.html`) 생성, 6 블록
- [x] `page.evaluate()` 로 블록 y좌표 추출: `[0, 1800, 3600, 5400, 7200, 9000, 10400]`
- [x] 그리디 분할: y=0~7200 + y=7200~10400 (2조각)
- [x] Pillow 크롭 → `bc7-01a.png`(450KB) + `bc7-01b.png`(199KB)
- [x] 블록 중간 절단 0건, 합계 = 원본 총 높이 확인
- [x] **SPEC §2-4 보완 필요 발견**: 마지막 조각은 4000px 미만 예외 허용 명시 (현재 3200px 생성). Phase B7 진입 시 SPEC 반영
- [x] `tasks/lessons.md` BC-7 섹션 기록

---

## ✅ Phase 1 — 크롤러 도메인 (SEO 트랙, SPEC-SEO-TEXT.md §3 [1][2])

> 본 체크박스는 stale 이었음. `domain/crawler/` + `tests/test_crawler/` 모두
> 이미 구현·검증되어 후속 Phase 2~U12 에서 활용 중. 2026-04-29 갱신.

- [x] `domain/crawler/model.py` — `SerpResult`, `BlogPage`, `InsufficientCollectionError`
- [x] `domain/crawler/brightdata_client.py` — 공통 HTTP, 재시도, 타임아웃
- [x] `domain/crawler/serp_collector.py` — 네이버 블로그 URL 필터, 최소 7개
- [x] `domain/crawler/page_scraper.py` — Web Unlocker 호출 (C1 결과 반영)
- [x] `application/stage_runner.py` 에 `run_stage_serp_collection`, `run_stage_page_scraping`
- [x] `tests/test_crawler/` 단위 테스트 — `test_brightdata_client.py`, `test_page_scraper.py`, `test_serp_collector.py`
- [x] 실제 키워드 end-to-end 수집 검증 (Phase U10~U12 흐름에서 활용)
- [x] `bash .claude/hooks/build-check.sh` 통과 (855 passed)

## 🚨 Phase 2 실측 이슈 (2026-04-16 발견, 후속 조치 대기)

- [x] **[P2-I1] 블로그 태그 수집 불가** — (c) **SPEC 전면 삭제** 채택 (2026-04-29). 사유: ① 모바일 본문에 태그 영역 부재 + 데스크톱 iframe 만 반환 ② 네이버 SEO 에서 해시태그는 마이너 시그널 (DIA+ 가중치 감소) ③ `related_keywords` 폴백으로 `suggested_tags` 추천 가능 ④ (a)/(b) 옵션의 추가 호출 비용·유지보수 부담이 효용 상회. SPEC-SEO-TEXT.md §3 [3]/[5]/[6] 정리, 코드 모델/필드는 호환성 유지 차원 빈 폴백 그대로 둠
  - [ ] 선택지 결정: (a) PostView.nhn iframe 실측, (b) 별도 JSON API 탐색, (c) SPEC 에서 전면 삭제
  - [ ] 결정 후 [5] cross_analyzer 의 `aggregated_tags` 와 [6] `suggested_tags` 폴백 로직 수정
  - 현재 상태: `PhysicalAnalysis.tags` 는 빈 리스트로 동작 (코드는 폴백 셀렉터 유지)

- [x] **[P2-I2] 네이버 블로거가 소제목을 잘 안 씀** — 10개 중 8개가 소제목 0개. 폰트 기반 감지는 정상 동작하나 원본 데이터가 부재. lessons.md P2 참조 — 2026-04-29 마감
  - [x] [4a] semantic_extractor 진입 시 "소제목 0개 → 전체를 단일 섹션으로 분류" 폴백 로직 추가 — `_build_user_content` 의 `subtitle_count == 0` 분기로 이미 적용 (기존)
  - [x] [5] cross_analyzer 구조 패턴 집계 시 소제목 있는 블로그만 대상으로 필터링 — `_classify_sections`/`_aggregate_distributions.ending_type`/`_extract_top_structures` 모두 섹션 ≥ 2 분모로 변경. 단일 섹션만 있을 시 빈 분류·빈 ending·빈 top_structures 반환 — 2026-04-29
  - [x] [6] outline_writer 의 "상위 글 구조 복제 금지" 지시를 "참고할 구조가 있으면" 로 조건부화 — `prompt_builder._build_structure_directive()` 신설, top_structures + sections.required 모두 비면 "구조 데이터 부재 — SEO 친화적 구조를 자체 설계" 분기 — 2026-04-29

## ✅ Phase 2~8 — SEO 트랙 (이미 구현·검증 완료)

> 본 섹션 체크박스는 stale 이었음. 실제로는 모든 SEO 트랙 도메인이 이미 구현·테스트·운영 중.
> 2026-04-29 갱신 — Phase 1 마킹 패턴과 동일하게 일괄 정리.

- [x] **Phase 2** 물리 분석 (`domain/analysis/physical_extractor.py`) — 이미지 메타 + DIA+ 7종 + 키워드 분석 + regression 테스트 (`tests/fixtures/naver_html/` 12개 실측 HTML)
- [x] **Phase 3** 의미 + 소구 + 교차 분석 (`semantic_extractor`, `appeal_extractor`, `cross_analyzer`, `pattern_card`) — [4a]/[4b] 분리 구현, schema_version "2.0", regression 테스트
- [x] **Phase 4** 생성 (`prompt_builder`, `outline_writer`, `body_writer`) — M2 불변 규칙 + image_prompts 생성 + `seo-writer-guardian` 에이전트 + `post-edit-lint.sh` 자동 차단
- [x] **Phase 5** 의료법 검증 — `CompliancePolicy` enum 전제 설계 ✅ 완료 (2026-04-29)
  - [x] `domain/compliance/rules.py` — `CompliancePolicy` enum (`SEO_STRICT`, `BRAND_LENIENT`) 정의 — 기존 적용
  - [x] `RULES: dict[CompliancePolicy, list[Rule]]` 구조로 두 프로필 동시 정의 — 기존 적용 (SEO_STRICT 10개 / BRAND_LENIENT 9개, FIRST_PERSON_PROMOTION 만 제외)
  - [x] `checker(text, policy=CompliancePolicy.SEO_STRICT)` 시그니처 — 기본값은 strict — 기존 적용 (`check_compliance`, `check_image_prompts` 모두)
  - [x] `fixer` 는 정책 독립적. SEO 트랙만 도입부 재생성 금지(M2) 추가 적용 — 기존 적용 (`fix_violations(..., policy, protect_intro: bool=True)`)
  - [x] 모든 SEO 트랙 호출부에 `policy=SEO_STRICT` 명시 전달 — `application/stage_runner.py` 5곳 + `application/orchestrator.py` 2곳 (`build_pre_generation_injection`/`check_compliance`/`fix_violations`/`check_image_prompts`) — 2026-04-29
  - [x] 사용자 제공 8개 카테고리 확정 시점에 `BRAND_LENIENT` 7개 초안 (§7-2) 도 함께 재검토 — SPEC-BRAND-CARD §7 항상 차단 9종 ↔ BRAND_LENIENT 9 카테고리 1:1 정합 검증, `tests/test_compliance/test_brand_lenient_coverage.py` (32 tests, R3 게이트) 신설 — 2026-04-29
  - [x] **⚠️ 순서 의존성**: Phase B7 (브랜드 카드 컴플라이언스) 는 이 Phase 5 완료 이후에만 착수 가능 — Phase B7 unblocked
- [x] **Phase 6** AI 이미지 생성 (`domain/image_generation/`) — Gemini 3.1 Flash Image Preview, SHA256 캐시 + 예산 가드 + 1회 재시도, 4개 모듈 + 4개 테스트 모두 구현·검증
- [x] **Phase 7** 조립 (`domain/composer/`) — assembler·outline_md·naver_html·quality_check, Layer 3 균등 이미지 배분 (`_build_even_image_map`), 네이버 HTML 화이트리스트
- [x] **Phase 8** 통합 + E2E — `run_pipeline` 본문 + 3계층 품질 강제 (Layer 1/2/3) + `quality-report.json` 자동 체크. build-check 912 passed, 75.73% cov

---

## 🎨 Phase B1~B9 — 브랜드 카드 트랙 (SPEC-BRAND-CARD.md §5)

> SEO 트랙과 완전 격리. `domain/brand_card/` 는 `domain/compliance/rules.py` 만 예외적 import.
> 2026-04-29 갱신 — 본 섹션 체크박스도 stale 이었음. 실제로는 Phase B1~B8 핵심이 거의 모두 구현·검증됨.
> SPEC 명명과 실제 파일명이 통합·재구성된 부분이 있어 매핑을 함께 표기. 진짜 잔여는 Phase B7 분할/메타 일부 + Phase B9 전체.

### Phase B1 — 도메인 스켈레톤 + 모델 ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/model.py` — 모든 모델 (`BrandProfile`/`BrandAssets`/`MediaAsset`/`BlockId` Enum 등) 구현
- [x] `domain/brand_card/storage.py` — Supabase CRUD (SPEC 의 `repository.py` 와 동치, 명명만 storage 로 통합)
- [x] `domain/brand_card/CLAUDE.md` — 도메인 규칙 + BRAND_LENIENT 9 매핑 표 (Phase 5 완료 갱신 반영)
- [x] `tests/test_brand_card/test_model.py` + `test_storage.py`
- [ ] **잔여**: `block_rules.py` 별도 파일로 분리되지 않음 — `model.py` 안의 `BlockId` Enum 외에 `BLOCK_MEDIA_MAPPING` 상수 명시적 정의 부재. 향후 §3-2-1 정합 검증 시 추가 검토

### Phase B2 — 브랜드 소스 로딩 + 자산 추출 ([B1][B2][B3]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/source_parser.py` — 홈페이지/txt/docx/pdf 수집 + BS4 전처리 + 로고 추출 (SPEC `source_loader.py` 와 동치)
- [x] `domain/brand_card/asset_merge.py` — Sonnet 자산 추출 + user_input + llm_extracted 머지 (SPEC 의 `asset_extractor` + `asset_merger` 통합)
- [x] `tests/test_brand_card/test_source_parser.py`, `test_asset_merge.py`
- [ ] **잔여**: `prompt_builder.py` 단일 진입점 미구현 — LLM 프롬프트가 `plan_generator.py` + `compliance.py` 에 분산. 단일 진입점 통합 필요 여부는 운영 안정 후 재검토
- [ ] **잔여**: `application/stage_runner.py` 의 `run_stage_brand_source_loading`/`run_stage_brand_asset_extraction` 미구현 — `application/brand_card_orchestrator.py` 가 도메인을 직접 호출. Phase B9 통합 시 일괄 정리

### Phase B3 — 카드 기획 ([B4] + [B4-v]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/plan_generator.py` — Opus 호출, BRAND_LENIENT 사전 주입, available_media 전달 (SPEC `card_planner.py` 와 동치)
- [x] `tests/test_brand_card/test_plan_generator.py`
- [ ] **잔여**: `card_plan_validator.validate_card_plan()` 별도 함수 미구현 — Pydantic `model_validator` 로 분산 검증. 명시적 [B4] 재호출 피드백 생성 로직 추가 검토 필요
- [ ] **잔여**: `application/stage_runner.run_stage_card_planning` 미구현 — Phase B9 통합 시 일괄 정리

### Phase B4 — 이미지 슬롯 생성 ([B5]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/image_prefetch.py` — Gemini Nano Banana 호출, sha256 캐시, fallback_text 분기 (SPEC `image_generator.py` 와 동치)
- [x] `tests/test_brand_card/test_image_prefetch.py`
- [ ] **잔여**: `application/stage_runner.run_stage_image_slot_generation` 미구현 — `brand_card_orchestrator._prefetch_ai_images` 가 인라인 처리. Phase B9 통합 시 정리

### Phase B5 — 템플릿 시스템 + HTML 합성 ([B6]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/templates/` 4종 — `clinic_trust`, `diet_empathy`, `local_info`, `process_guide` (각 `card.html.j2` + `style.css` + `meta.json`)
- [x] `domain/brand_card/template_registry.py` — meta.json 로드
- [x] `domain/brand_card/renderer.py` — Jinja2 합성 + Playwright (SPEC `html_renderer.py` + `playwright_renderer.py` 통합)
- [x] `tests/test_brand_card/test_renderer.py`, `test_template_registry.py`
- [ ] **잔여**: 5번째 템플릿 미구현 — SPEC §B5 는 5종 명시. 운영 키워드 다양성 확인 후 추가 여부 결정
- [ ] **잔여**: `application/stage_runner.run_stage_card_html_render` 미구현 — Phase B9 통합 시 정리

### Phase B6 — 브랜드 카드 컴플라이언스 ([B7]) ✅ (2026-04-29 완료)
- [x] Phase 5 (SEO 컴플라이언스) 완료 — `CompliancePolicy.BRAND_LENIENT` 프로필 정의 + R3 게이트 회귀 테스트 통과
- [x] `domain/brand_card/compliance.py` — `CompliancePolicy.BRAND_LENIENT` 호출, 블록 카피 교체 fixer
- [x] `tests/test_brand_card/test_compliance.py` + `test_brand_lenient_coverage.py`
- [ ] **잔여**: `application/stage_runner.run_stage_card_compliance` 미구현 — Phase B9 통합 시 정리

### Phase B7 — Playwright 렌더링 ([B8]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/renderer.py` — sync Chromium 세션, 폰트 로드 대기, `page.evaluate` overflow 검출, `page.screenshot` (clip)
- [x] `tests/test_brand_card/test_renderer.py`
- [ ] **P1 잔여 (B9 와 통합)**: `application/stage_runner.run_stage_card_screenshot` — Phase B9 의 stage_runner 통합 작업에 흡수

> **2026-04-29 재분류**: 9000px 자동 분할 + PNG tEXt 메타 + hard max 18000 variant 분류 3건은 SPEC v2 (`§2 P1 제외`, `§3` 1080×1350/1920 인스타 카드 사이즈) 에 따라 P1 영역 아님. 아래 "📦 P2 이후 — long-form 확장 트랙" 섹션으로 이동.

### Phase B8 — 패키지 정리 + manifest ([B9]) ✅ (2026-04-29 stale 정리)
- [x] `domain/brand_card/manifest.py` — cards-manifest.json 생성 (SPEC `manifest_builder.py` 와 동치)
- [x] `application/brand_card_orchestrator.render_card_set` — SPEC `orchestrator.run_brand_card_only` 와 동치
- [x] `tests/test_brand_card/test_manifest.py`

### Phase B9 — 합류 + 통합 (`run_full_package`) ✅ 완료 (2026-04-29)
- [x] `application/orchestrator.run_full_package` — ThreadPoolExecutor(max_workers=2) 병렬 실행, 한쪽 실패가 다른 쪽을 종료시키지 않으며 결과 보존
- [x] `application/orchestrator.run_brand_card_only` — auto_approve 분기 (draft 게이트 vs [B12] 일괄)
- [x] `application/models.py` 에 `PackageResult`, `BrandCardResult` 추가
- [x] `scripts/register_brand.py`, `scripts/generate_cards.py`, `scripts/run_full_package.py`, `scripts/remove_media.py` CLI 래퍼 4종
- [x] 단위 테스트 7건 (`tests/test_application/test_orchestrator.py::TestRunBrandCardOnly`, `::TestRunFullPackage`) — draft/auto_approve, 0개 plan, 예외, 양쪽 성공/부분 성공/양쪽 실패 분기
- [ ] **선택**: `.claude/skills/brand-card/` 스킬 + `.claude/agents/domain/brand-card-guardian.md` 에이전트 — 도메인 일관성 가디언, 운영 안정 후 추가 검토
- [ ] **잔여**: 실 키워드 + 실 브랜드로 `run_full_package` 끝까지 통과시키는 통합 E2E 테스트 — Bright Data/Anthropic/Gemini/Supabase 실호출 필요. 운영 진입 시점에 별도 진행

---

## 🔍 Phase K1~K6 — 키워드 노출 난이도 분석 (2026-04-29 착수)

> 새 키워드 등록 전 SERP 1페이지 구성을 분석해 블로그 진입 난이도를 자동 판정하는 도구.
> 정기 수집 X, 사용자 수동 트리거. 단일/대량 분석 가능. 별도 `/keywords` 페이지.
> 등급 산출 공식 (대화 기반 합의):
> - `B`=블로그 슬롯 (VIEW+인플루언서+블로그통합), `D`=도배 카드 (광고+플레이스+쇼핑+위젯), `T`=총 카드
> - 점수 = `D × 1.5 - B × 3` (낮을수록 유리)
> - 등급: `T<8 OR B==0` → 미노출 / `B≤2 AND D/T≥0.5` → 상 / `B≥5` → 하 / 그 외 → 중

### Phase K1 — 도메인 + 파서 골격 ✅ 완료 (2026-04-29)
- [x] K1.1 `domain/keyword_difficulty/__init__.py` + `CLAUDE.md`
- [x] K1.2 `model.py` — `SerpSection` Enum (10종), `SerpComposition`, `DifficultyGrade` Enum, `KeywordDifficulty`
- [x] K1.3 `parser.py` — 네이버 SERP HTML → SerpComposition (sc_new 섹션 분류 + URL 패턴 카드 카운트)
- [x] K1.4 `scorer.py` — `score = D × 1.5 - B × 3`, 4단계 등급 (MISSING/HIGH/MEDIUM/LOW)
- [x] K1.5 `tests/test_keyword_difficulty/` (test_parser + test_scorer 22 tests)
- [x] K1.6 `architecture-check.sh` `[keyword_difficulty]=0` 등록

### Phase K2 — PoC 실측 ✅ 완료 (2026-04-29)
- [x] K2.1 fixture HTML 8개 fetch 완료 (다이어트약/다이어트보조제/다이어트운동/살빼는방법/천안다이어트한의원/부평다이어트한의원/BMI계산하기/감비정)
- [x] K2.2 파서 결과 검증 — 등급이 합리적으로 매핑 (광역 정보성 → low/medium, 광고도배+블로그4슬롯 → medium, 롱테일 → low)
- [x] K2.3 네이버 SERP 구조 (React 디자인 시스템 + 동적 해시 클래스) 대응 휴리스틱 적용
- [x] K2.4 `tasks/lessons.md` K2 섹션에 셀렉터 + PoC 결과 + 한계점(위젯 식별 강화 / 광고 가중치 / 인플루언서 분리) 기록

### Phase K3 — Supabase + storage + application ✅ 코드 완료, ⏸ Supabase 스키마 적용 대기
- [x] K3.1 `config/schema.sql` 13번 섹션에 `keyword_difficulty_snapshots` 테이블 SQL 추가
- [x] K3.1.b Supabase 대시보드 SQL Editor 적용 완료 — 2026-04-29 (rows=0 확인)
- [x] K3.2 `domain/keyword_difficulty/storage.py` — `insert_snapshot`, `get_latest`, `list_recent`, `list_by_grade`, `list_keyword_history`
- [x] K3.3 `application/keyword_difficulty_orchestrator.py` — `analyze_keyword`, `batch_analyze_keywords` (ThreadPool max=3, 1초 rate limit)
- [x] K3.4 단위 테스트 (mock Bright Data + Supabase) — 7건 통과

### Phase K4 — CLI ✅ 완료
- [x] K4.1 `scripts/analyze_keyword_difficulty.py` — `--keyword` 또는 `--file`, `--no-persist`, 결과 표 출력
- [ ] K4.2 ~~`tests/test_scripts/test_keyword_difficulty_cli.py`~~ — argparse 단위 테스트는 실 SERP 호출이 필요해 skip

### Phase K5 — Web UI ✅ 완료
- [x] K5.1+K5.2 `web/api/routers/keyword_difficulty.py` — 4 엔드포인트 (analyze/batch/snapshots/list) + Pydantic 스키마 인라인 정의
- [x] K5.3 `web/api/main.py` 에 라우터 등록 (`/api/keyword-difficulty/*`)
- [x] K5.4 frontend `types/index.ts` (`DifficultyGrade`, `KeywordDifficulty`) + `lib/api.ts` 4 함수
- [x] K5.5 `web/frontend/src/app/keywords/page.tsx` — 단일/대량 입력 + 등급 필터 + 검색 + 정렬 표
- [x] K5.6 nav 에 `/keywords` 링크 추가

### Phase K6 — 검증 + 커밋
- [x] K6.1 `bash .claude/hooks/build-check.sh` 그린 — 952 passed, 75.49% cov
- [ ] K6.2 수동 smoke (Supabase 스키마 적용 후) — 단일 분석 + 10개 대량 → /keywords 페이지에서 등급 표시 확인
- [ ] K6.3 commit + push

### Phase K7 — 네이버 검색광고 API 통합 (월 검색량 표시) ✅ 코드 완료, ⏸ 사용자 작업 2건
- [x] K7.1 `domain/keyword_difficulty/naver_ad_client.py` — HMAC SHA256 서명 + `get_search_volume(keyword)` (실패 시 None)
- [x] K7.2 `model.py` 에 `SearchVolume` + `KeywordDifficulty.search_volume`
- [x] K7.3 `config/settings.py` 에 `naver_ad_api_key/secret_key/customer_id` 3개 추가
- [x] K7.4 `application/keyword_difficulty_orchestrator.analyze_keyword` — SERP + 검색량 순차 호출 (병렬은 contextvars 격리로 usage 추적 누락)
- [x] K7.5 `config/schema.sql` 에 `monthly_pc_search/monthly_mobile_search/monthly_total_search/competition_idx` 칼럼 추가 (idempotent ALTER 포함)
- [ ] K7.5.b **사용자 작업**: Supabase SQL Editor 에서 ALTER TABLE 실행 (또는 schema.sql 13번 섹션 재실행 — IF NOT EXISTS 라 안전)
- [x] K7.6 `storage.py` insert/조회 갱신
- [x] K7.7 `web/api/routers/keyword_difficulty.py` 응답 4 필드 추가
- [x] K7.8 Frontend `/keywords` 페이지 — "월 검색량" / "PC / 모바일" / "경쟁" 3 컬럼 추가
- [x] K7.9 `naver_ad_client` 가 `record_usage(provider="naver_searchad", model="keywordstool")` 자동 호출
- [x] K7.10 단위 테스트 — `test_naver_ad_client.py` 14건 (HMAC 서명 / 응답 파싱 / 인증 누락 / HTTP 에러 / 네트워크 예외)
- [ ] K7.11 **사용자 작업**: Render 환경 변수 추가 — `NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`, `NAVER_AD_CUSTOMER_ID`

---

## ⚡ Phase F1~F5 — 키워드 분석 속도 개선 (2026-04-29 착수)

> 현재 단일 6~12초 / 배치 50개 약 200초. 사용자 결정: 1~5번 모두 순차 적용.

### Phase F1 — 배치 병렬도 상향 ✅ 완료 (2026-04-29)
- [x] F1.1 `_BATCH_DEFAULT_PARALLEL` 3 → 8, `_BATCH_RATE_LIMIT_SEC` 1.0 → 0.3
- [x] F1.2 `_BatchRequest.parallel` 상한 5 → 10, 기본 8

### Phase F2 — 단일 분석 검색량 병렬화 ✅ 완료 (2026-04-29)
- [x] F2.1 `analyze_keyword` 가 `run_in_isolated_usage_ctx` + ThreadPool(2) 로 SERP + 검색량 병렬 호출. 워커 usage 를 부모로 머지해 추적 보존
- [x] F2.2 캐시 hit 시 검색량만 단일 호출 (격리 ctx 불필요)

### Phase F3 — SERP 캐싱 ✅ 완료 (2026-04-29)
- [x] F3.1 `domain/keyword_difficulty/cache.py` — TTL 30분 LRU, 스레드 안전 (`threading.Lock`), max 256 entries
- [x] F3.2 orchestrator 가 캐시 hit 시 Bright Data 호출 우회. record_usage 안 됨
- [x] F3.3 단위 테스트 8건 (TTL 만료 / LRU evict / hits·misses / clear)

### Phase F4 — 사용자 체감 개선 ✅ 완료 (2026-04-29)
> Backend 진짜 비동기(job_manager) 대신 Frontend 청크 분할 채택. 인프라 추가 없이 체감 개선 동등.
- [x] F4.1 `/keywords` 페이지 — 50개 입력을 8개 청크로 분할 후 순차 호출
- [x] F4.2 청크 완료 시점에 부분 결과 즉시 표 갱신 (`reload()` 청크별 호출)
- [x] F4.3 진행률 바 표시 (`done / total`) — 완료마다 시각화
- [x] F4.4 단일 분석은 동기 유지 (병렬화로 6~10초 내 응답)

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

## ☁️ Phase D1~D5 — 클라우드 배포 (Vercel + Render, 2026-04-29 착수)

> 노트북 의존성 0. 어디서든 `*.vercel.app` 접속 시 항상 응답.
> Frontend = Vercel Hobby (free), Backend = Render Starter ($7/월), DB/Storage = Supabase (이미).
> 자동 도메인으로 시작 → 안정화 후 커스텀 도메인 검토.

### Phase D1 — 백엔드 컨테이너 + Storage ✅ (대부분 사전 구현됨)
- [x] `Dockerfile` — Python 3.11 + Playwright Chromium + 의존성 캐시 레이어 (이전 작업)
- [x] `render.yaml` — `plan: starter` 로 변경 (always-on)
- [x] `domain/storage/supabase_storage.py` — `upload_bytes`, `get_signed_url` (이전 작업)
- [x] `application/stage_runner.py` — output 저장 시 Supabase Storage 동시 업로드 (이전 작업)
- [x] `web/api/routers/results.py` — 조회 시 signed URL 리다이렉트 (이전 작업)
- [x] `config/settings.py` — `cors_origins`, `admin_api_key`, `storage_bucket` (이전 작업)

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

## ✅ Phase R1~R7 — 순위 추적 시스템 MVP (이미 구현·검증 완료)

> 본 섹션 체크박스도 stale 이었음. 실제로는 모든 R1~R7 작업이 구현·테스트·운영 중.
> 2026-04-29 갱신 — Phase 1 / Phase 2~8 / Phase B1~B8 와 동일한 stale 정리 패턴.
> 운영 중 발견된 실측 피드백 / 다중 publication / cannibalization 처리는 Phase U10~U12 에서 후속 처리. SPEC-RANKING.md 참조.

- [x] **R1** Backend Foundation — `domain/ranking/` 8개 (`model/url_match/tracker/storage/serp_parser/publication_actions/state_calculator/__init__`) + `tests/test_ranking/` 7개. `architecture-check.sh` `STAGE_ORDER[ranking]=0` 격리 도메인 등록 + `domain/ranking/CLAUDE.md`
- [x] **R2** Application — `application/ranking_orchestrator.py` (register/check/check_all) + `application/scheduler.py` (APScheduler AsyncIOScheduler, cron `09:00 Asia/Seoul`) + `tests/test_application/test_ranking_orchestrator.py`, `test_scheduler.py`
- [x] **R3** API — `web/api/routers/rankings.py` 5 엔드포인트 + `web/api/main.py` lifespan 스케줄러 통합
- [x] **R4** CLI — `scripts/register_publication.py`, `scripts/check_rankings.py`
- [x] **R5** Frontend — `web/frontend/src/components/PublicationForm.tsx`, `RankingTimeline.tsx`, `app/rankings/page.tsx`, `lib/api.ts` 5 함수
- [x] **R6** Tests — `tests/test_ranking/` 7개 + `tests/test_web/test_rankings_api.py`. 920 passed 75.89% cov
- [x] **R7** 검증 — build-check 그린, ranking 도메인 격리 통과, 운영 중

<details>
<summary>원본 R1~R7 상세 체크리스트 (참고용 보존)</summary>

### R1.1 Supabase 마이그레이션
- [x] R1.1.1 `config/schema.sql` 끝에 `publications` 테이블 SQL 추가
- [x] R1.1.2 같은 파일에 `ranking_snapshots` 테이블 SQL 추가
- [x] R1.1.3 Supabase 대시보드 SQL Editor 에 적용
- [x] R1.1.4 `tasks/lessons.md` 에 결과 기록

### R1.2~R1.7 도메인 모델·URL 매칭·tracker·storage·CLAUDE.md·architecture-check
- [x] 모두 구현 완료 — `domain/ranking/` 8개 + `tests/test_ranking/` 7개

### R2.1~R2.4 application 오케스트레이션·스케줄러·테스트
- [x] 모두 구현 완료 — `application/ranking_orchestrator.py`, `application/scheduler.py` (APScheduler `AsyncIOScheduler` cron `09:00 KST`)

### R3.1~R3.4 API 라우터·lifespan·테스트·문서
- [x] 모두 구현 완료 — `web/api/routers/rankings.py` 5 엔드포인트 + lifespan 통합

### R4.1~R4.3 CLI 2종 + README
- [x] 모두 구현 완료 — `scripts/register_publication.py`, `scripts/check_rankings.py`

### R5.1~R5.6 Frontend
- [x] 모두 구현 완료 — `PublicationForm.tsx`, `RankingTimeline.tsx`, `app/rankings/page.tsx`, `lib/api.ts` 5 함수

### R6.1~R6.3 Tests
- [x] 모두 구현 완료 — `tests/test_ranking/` + `tests/test_web/test_rankings_api.py`. lessons.md 패턴 기록 완료

### R7.1~R7.7 검증 + 커밋
- [x] build-check 그린 + architecture 격리 통과 + 운영 중

</details>

---

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

## Phase U0: 공통 레이아웃 + 캘린더 sticky/내부스크롤 (P0) ✅ 완료 (2026-04-27)
- [x] U0.1 `layout.tsx` — `max-w-5xl` → `max-w-[1440px]`, `py-6` → `py-3`, header `py-3` → `py-2`
- [x] U0.2 캘린더 — 뒤로가기 + h1 + 월컨트롤 + 검색 1줄 통합, `space-y-4` → `space-y-2`
- [x] U0.3 캘린더 테이블 컨테이너 `max-h-[calc(100vh-160px)] overflow-auto`, `<thead> th` `sticky top-0`
- [x] U0.4 캘린더 헤더 교차 모서리 `z-30`, 일자 헤더 `z-20`, 키워드 데이터 셀 `z-10`
- [x] U0.5 typecheck 통과 (`npx tsc --noEmit` 무에러). lint 스크립트 없음

## Phase U1: 캘린더 컴팩트 + 운영홈 행 압축 (P1) ✅ 완료 (2026-04-27)
- [x] U1.1 캘린더 셀 `28×28` ↔ `22×20`, 키워드열 `180px` ↔ `160px` 동적
- [x] U1.2 컴팩트 토글 버튼 (기본 ON `압축`, 클릭 시 `확장`)
- [x] U1.3 `PublicationActionRow.tsx` 1줄 압축 — 4행 → 1행 (`flex flex-wrap`), 패딩 `p-3` → `px-3 py-1.5`
- [x] U1.4 진단 권장 액션은 인라인 + `title` 툴팁 (URL 도 `↗` 아이콘 + tooltip)

## Phase U2: 캘린더 그룹핑 / 결과·작업·사용량 2-pane (P2) ✅ 완료 (2026-04-27)
- [x] U2.1 캘린더 키워드 그룹핑 — 이후 사용자 요청으로 제거 (refactor)
- [x] U2.2 `results/[slug]/page.tsx` 2-pane — `grid grid-cols-12 lg:col-span-4 + lg:col-span-8` + 좌측 sticky
- [x] U2.3 `ProgressTracker.tsx` 컴팩트 — `p-6 mb-6` → `p-3 mb-3`, 아이콘 `8×8` → `6×6`, currentDetail 인라인
- [x] U2.4 `UsageDashboard.tsx` — 기간선택+요약카드 1줄, 일별/작업별 `grid lg:grid-cols-12 (7+5)` 병렬 + sticky thead
- [x] U2.5 캘린더 헬퍼 컴포넌트를 `components/CalendarTable.tsx` 로 분리 (300줄 한계 준수)

## Phase U9: 브랜드 카드 트랙 Phase 0 + Phase 1 Day 1 (2026-04-28) ✅ 진행 중

### Phase 0: 결정 게이트 (1시간) ✅
- [x] `architecture-check.sh` `[brand_card]=0` 격리 도메인 등록
- [x] `brand_card → compliance` 만 허용하는 특별 예외 블록 추가 (SPEC §10)
- [x] architecture-check 통과 확인

### Phase 1 Day 1 ✅ 완료 (마이그레이션 + 모델 + CLAUDE.md + 검증 게이트)
- [x] `config/migrations/2026-04-28_brand_card_v2_1.sql` — brand_message_sources, card_campaign_inputs 신규 + brand_cards ALTER 6 컬럼 + 검증/롤백 SQL 주석
- [x] `domain/brand_card/__init__.py` — 도메인 격리 docstring
- [x] `domain/brand_card/model.py` — Pydantic 모델 + Enum 6종 (CardStrategy/ExpressionLevel/BrandCardStatus/CardType/MessageSourceType + 모델 8종)
- [x] `domain/brand_card/CLAUDE.md` — 격리 원칙·진입점 분리·파일 책임·다양화 정의·BRAND_LENIENT 정책·명명 규칙
- [x] `tests/test_brand_card/test_model.py` — 19 시나리오 (Enum 5 + 모델 14)
- [x] `tests/test_brand_card/test_brand_lenient_coverage.py` — Phase 1 검증 게이트 (R3): SPEC §7 항상 차단 9종 vs 현재 7종 catch + 갭 2종(부작용 없음/가격 할인 과장) xfail 마킹

### Phase 1 Day 2 ✅ 완료 (storage + source_parser + asset_merge + reuse_guard)
- [x] `storage.py` — Supabase CRUD 11 함수 (brand_message_sources / card_campaign_inputs / brand_cards). 신규 컬럼만 read/write, 기존 컬럼은 호환성 유지 (deprecate)
- [x] `source_parser.py` — txt/docx/pdf/html 텍스트 추출. BC-3 lessons (pypdf → pdfplumber fallback) + BC-4 lessons (python-docx) 반영
- [x] `asset_merge.py` — SPEC §6 5단계 우선순위 병합. MergedAssets 데이터클래스. 1) brief 2) attached 3) brand_common 4) other_references
- [x] `reuse_guard.py` — 차단(headline 30일) + 경고(template 5회/strategy 5회/photo 3 키워드) + override 옵션 (D5)
- [x] `tests/test_brand_card/test_asset_merge.py` 7 시나리오
- [x] `tests/test_brand_card/test_reuse_guard.py` 13 시나리오 (블락/경고/override)

### Phase 1 Day 3 ✅ 완료 (plan_generator.py — Phase 1 마지막 핵심 모듈)
- [x] `domain/brand_card/plan_generator.py` — LLM tool_use 카드 기획안 생성기
- [x] `_build_system_prompt(level)` — BRAND_LENIENT 9 룰 description 자동 주입 + 표현 강도(safe/balanced/hooking) 가이드 + tool_use 강제 문구
- [x] `_build_user_prompt(...)` — 키워드/전략/템플릿/표현강도 + asset_merge 5단계 우선순위 자산 단락 + reuse_guard 차단/경고 제약
- [x] `_build_tool_schema()` — `submit_brand_card_plan` ToolParam (angle + blocks 4~6개 + 카드 타입 6 enum + recommended_position 4 enum)
- [x] `_invoke()` — Sonnet 4.6 + tool_choice forced + ApiUsage 기록 (cache_control: ephemeral)
- [x] `_extract_tool_input()` / `_parse_plan()` — 응답 검증 + Pydantic BrandCardPlan 인스턴스 생성 (status=draft)
- [x] `tests/test_brand_card/test_plan_generator.py` — 26 시나리오 (system/compliance/expression/user/assets/reuse/schema/extract/parse + happy path mock)

### Phase 1 종료 — 검증
- [x] `bash .claude/hooks/build-check.sh` ✓ PASSED 모든 단계
- [x] 테스트 634 → **660 passed** (+26)
- [x] 커버리지 71.32% 유지

## Phase U10: 브랜드 카드 Phase 2 (2026-04-28 진행) — application + 렌더링

### Phase 2.0 ✅ application/brand_card_orchestrator.py
- [x] `generate_card_plan(brand_id, keyword, expression_level, strategy_count, allow_reuse_override)` — N variant 묶음 생성, reuse_group_id 공유, 모두 status=draft 저장
- [x] strategy → template_id 매핑 (trust_first → clinic_trust 등)
- [x] approve_plan / reject_plan — status 전이 ([B6])
- [x] render_card_set — Phase 2.5 placeholder (NotImplementedError)
- [x] 자산 fetch (campaign + attached + brand) → asset_merge → reuse_guard → plan_generator 통합 흐름
- [x] `tests/test_application/test_brand_card_orchestrator.py` — 8 시나리오 (N variants / shared group_id / invalid count / strategy mapping / storage insert / approve / reject / render placeholder)

### Phase 2.1 ✅ 템플릿 1종 (clinic_trust) + template_registry
- [x] `template_registry.py` — TemplateMeta dataclass + get_template + list_templates + validate_card_type_compat
- [x] `templates/clinic_trust/meta.json` — 1080×1350, 6 card_types 모두 지원, 신뢰형 네이비/화이트 팔레트
- [x] `templates/clinic_trust/style.css` — Pretendard @font-face (PRETENDARD_URL placeholder), card_type 별 미세 조정 (problem=red tag, solution=green, process=numbered list, hero=84px headline)
- [x] `templates/clinic_trust/card.html.j2` — Jinja2, 6 card_type 분기, data-text-block 속성으로 overflow 검출 표시
- [x] `tests/test_brand_card/test_template_registry.py` — 6 시나리오 (load/files exist/unknown raise/list/compat/all six types)
- [x] 나머지 3 템플릿 (diet_empathy/process_guide/local_info) — clinic_trust 패턴 기반 자체 프로토타이핑 (a+b 조합) (2026-04-29)
  - `diet_empathy` — warm coral (#E76F51 / #FCD5CE / #FFF8F4), 다이어트 공감형, 친근한 라벨 ("이런 고민" / "함께 풀어요" 등)
  - `process_guide` — muted teal (#2A9D8F / #E9F5F4 / #1F2D2C), 단계 강조, → 화살표 마커, process step 56px box
  - `local_info` — forest green (#2C5F2D / #FAEBD7 / #FFF8E7), CSS 위치 핀 아이콘, 다이아몬드 마커, 동네 친화 라벨
  - 4종 parametrize 회귀 테스트: 21 passed (load/files/meta_human_fields/all_p1_card_types)
  - **사용자 디자인 피드백 시 색상/라벨/디테일 조정** — 시안 또는 단순 컨펌 제공 시 후속 차수에서 반영

### Phase 2.2 ✅ Playwright PNG 렌더러 + overflow 검출
- [x] `domain/brand_card/renderer.py` — sync API (G3=A), 1080×1350 viewport
- [x] `_prepare_html` — Jinja2 렌더 + style.css PRETENDARD_URL → file:// 치환 (G4=B, assets/fonts/Pretendard-Regular.woff2)
- [x] `_render_with_playwright` — file:// 로딩 + document.fonts.ready 대기 + page.evaluate() overflow 검출 + screenshot
- [x] M6: overflow 검출 시 `TextOverflowError` raise (data-text-block 별 scrollW/H 비교)
- [x] `RenderContext` 데이터클래스 (block + brand_name + brand_url + image_url)
- [x] `cleanup_work_dir` — 디버깅 후 임시 정리
- [x] `tests/test_brand_card/test_renderer.py` — 11 시나리오 (HTML/CSS 작성 / 폰트 placeholder 치환 / 이미지 URL 임베드 / placeholder / card_type class / data-text-block / subcopy 생략 / overflow raise / mock screenshot / cleanup)

### Phase 2.3 ✅ AI 이미지 prefetch ([B8.5])
- [x] `domain/brand_card/image_prefetch.py` — CardBlock → ImagePrompt dict 변환 어댑터 (build_image_prompts + map_results_to_blocks)
- [x] block index ↔ sequence 양방향 매핑으로 generate_images 결과를 block 단위로 재배포
- [x] `image_type` card_type 기반 추론 (hero/trust=photo, process=diagram, 그외=illustration)
- [x] `application/brand_card_orchestrator._prefetch_ai_images` — domain/image_generation 합성 호출
- [x] `settings.brand_card_image_budget_per_set = 6` 가드 추가
- [x] `tests/test_brand_card/test_image_prefetch.py` — 8 시나리오

### Phase 2.4 ✅ manifest + 보관함 경로
- [x] `domain/brand_card/manifest.py` — build_manifest + write_manifest. SPEC §3 형식 (brand_id/keyword/generated_at/cards[])
- [x] 카드 entry: template_id/strategy/expression_level/variant_idx/path/compliance_passed
- [x] 한글 보존 (`ensure_ascii=False`)
- [x] `output_root/{reuse_group_id}/cards-manifest.json` 저장 경로
- [x] `tests/test_brand_card/test_manifest.py` — 5 시나리오

### Phase 2.5 ✅ render_card_set 본격 구현
- [x] `application/brand_card_orchestrator.render_card_set(reuse_group_id, output_root, brand_name, brand_url, media_path_resolver)` 진입점
- [x] approved plan 만 진행 (BrandCardError 명시 raise)
- [x] [B8.5] AI 이미지 prefetch → block 별 PNG 경로 매핑
- [x] block 별 renderer.render_card_to_png 호출 (variant_idx 1-based)
- [x] SPEC §3 파일명: `card-{template_id}-{strategy}-{NN}.png`
- [x] `_resolve_image_url`: image_asset_id (실사) 우선 → ai_image_paths 폴백 → None
- [x] manifest 저장 + plan status 전이 (approved → published)
- [x] `tests/test_application/test_brand_card_orchestrator.py` Phase 2.5 케이스 +3 (no plans/no approved/renders+manifest/filename)

### Phase 1 검증
- [x] `bash .claude/hooks/build-check.sh` ✓ PASSED
- [x] 테스트 583 → **611 passed + 2 xfailed** (+30, 새 카테고리 결정 게이트 가시화)
- [x] 커버리지 70.82% → **71.31%**

### 사용자 결정 게이트 G1 ✅ 완료 (옵션 A 선택, 2026-04-28)
- [x] `ViolationCategory.NO_SIDE_EFFECTS_CLAIM` 신규 — `_NO_SIDE_EFFECTS_CLAIM` Rule
- [x] `ViolationCategory.PRICE_DISCOUNT_HYPE` 신규 — `_PRICE_DISCOUNT_HYPE` Rule
- [x] 양 정책(SEO_STRICT 8→10, BRAND_LENIENT 7→9) 매핑
- [x] SPEC-SEO-TEXT.md §5 의료법 10개 카테고리 표 갱신 (도입 시점 명시)
- [x] domain/compliance/CLAUDE.md 카테고리 변경 시 의무 절차 5단계 명시
- [x] tests/test_compliance/test_rules.py 카운트 어서션 갱신 (8→10, 7→9)
- [x] tests/test_brand_card/test_brand_lenient_coverage.py xfail 제거, §7 9/9 매핑 검증

## Phase U11: 브랜드 카드 Phase 3 (2026-04-28) ✅ — 컴플라이언스/운영

### Phase 3.1 ✅ domain/brand_card/compliance.py 신규
- [x] `validate_brand_card_plan(plan, *, max_iterations=2)` — BRAND_LENIENT checker/fixer wrapper
- [x] phrase replacement 만 수행 (paragraph regeneration 미사용 — 블록 텍스트가 짧아 비용 대비 의미 적음)
- [x] `ai_image_prompt` 별도 검증 — `image_prompt_validator` 호출, 위반 시 `None` 으로 비움 + changelog
- [x] expression_level 차등: `safe` 일 때만 hooking 표현 6종(실패했다면, 굶는, 혼자 버티 등) 추가 경고. 텍스트는 수정 안 함, changelog 만 기록
- [x] 알 수 없는 카테고리(LLM 환각) 방어 — `_is_known_category` 가 ViolationCategory enum 검증

### Phase 3.2 ✅ 상태 전이 검증 (SPEC §9.3)
- [x] `domain/brand_card/model.py` — `StatusTransitionError` 예외 + `_VALID_STATUS_TRANSITIONS` dict
- [x] `assert_status_transition(current, target)` — 허용되지 않은 전이 시 raise. 동일 상태는 idempotent
- [x] 전이도: draft → reviewed/approved/rejected, reviewed → approved/rejected, approved → published/rejected, published → archived. rejected/archived 는 종결

### Phase 3.3 ✅ orchestrator 통합
- [x] `generate_card_plan`: plan_generator 출력 → `bc_compliance.validate_brand_card_plan` → `source_summary["compliance_report"]` 병합 → storage 저장. 위반 fix 실패 시 plan 은 `draft` 유지 (사용자 판단 위임)
- [x] `approve_plan` / `reject_plan`: `_transition_plan(plan_id, target)` 헬퍼로 전이 검증 후 storage 호출. 누락 plan 은 `None` 반환
- [x] `render_card_set`: 렌더 직전 최종 재검증 → `RenderedBrandCard.compliance_report` 실데이터 채움. `update_card_status` 에 `compliance_report` 함께 전달 (storage 가 jsonb 저장)
- [x] `_render_plan_blocks`: `compliance_report: ComplianceReport | None` 파라미터 추가, placeholder `{"passed": True}` 제거

### Phase 3.4 ✅ 테스트
- [x] `tests/test_brand_card/test_compliance.py` 신규 — 31 시나리오 (clean/violation/iter cap/unknown category/image prompt/expression_level 3종/multi-block/final_text/status transition matrix 17 케이스)
- [x] `tests/test_application/test_brand_card_orchestrator.py` Phase 3 5 케이스 추가:
  - generate compliance 호출 횟수 / source_summary 병합 / 위반 시 draft 유지
  - render compliance_report 카드 propagate / status 전이 검증
- [x] 기존 fixture (`storage_mock`/`plan_gen_mock`) 에 `compliance_mock` 추가
- [x] approve/reject 테스트를 `get_card_plan` mock 으로 갱신, 잘못된 전이 케이스 + idempotent + None 반환 케이스 추가

### Phase 3 검증
- [x] `bash .claude/hooks/build-check.sh` ✓ PASSED
- [x] 테스트 660 → **801 passed** (+141)
- [x] 커버리지 71.31% → **76.24%**

## Phase U12: 브랜드 카드 Phase 4.1 (2026-04-28) ✅ — 백엔드 API 라우터

### Phase 4.1 ✅ web/api/routers/brand_studio.py 신규 (10 routes)
- [x] GET /brands — 브랜드 목록
- [x] GET /brands/{id}/sources — 메시지 소스 목록
- [x] POST /brands/{id}/sources — multipart 업로드 (txt/docx/pdf/html → source_parser)
- [x] POST /brands/{id}/campaign-inputs — 캠페인 입력 저장
- [x] POST /brands/{id}/plans — orchestrator.generate_card_plan (LLM 동기)
- [x] GET /plans/{group_id} — 묶음 조회
- [x] POST /plans/{plan_id}/approve | /reject — StatusTransitionError → 409
- [x] POST /plans/{group_id}/render — JobManager.submit_brand_card_render (job_id 반환, 202)
- [x] GET /cards/{group_id} — 8 항목 결과 보관함 + png_paths

### Phase 4.1 인프라
- [x] domain/brand_card/storage.py — list_brands / get_brand / list_media_assets / get_media_asset / insert_media_asset 추가
- [x] domain/brand_card/model.py — BrandProfile / BrandMediaAsset Pydantic 추가
- [x] web/api/job_manager.py — submit_brand_card_render + _dispatch 분기 (brand_card_render → application.brand_card_orchestrator.render_card_set)
- [x] web/api/main.py — brand_studio.router 등록
- [x] pyproject.toml — `python-multipart>=0.0.9` web extras 추가, 환경에 설치 완료

### Phase 4.1 테스트
- [x] tests/test_web/test_brand_studio_api.py 신규 — 25 시나리오:
  - list_brands(2) / sources(6) / campaign_input(1) / generate(3) / get_plans(2) / approve_reject(4) / render(3) / archive(2) / auth(2)
- [x] FastAPI TestClient + monkeypatch + multipart 업로드 검증
- [x] 변경 영향 범위 회귀: tests/test_brand_card + test_application + test_compliance + test_web/test_brand_studio = **298 passed**

### Phase 4.1 검증
- [x] ruff check — All checks passed
- [x] ruff format — applied (2 files)
- [x] pyright — 0 errors / 0 warnings
- [x] 관련 테스트 298 passed

### Phase 4.2 — 프론트엔드 UI (2026-04-28) ✅
- [x] `lib/brand-studio-api.ts` — 9 헬퍼 + 타입 (Pydantic 1:1, 도메인 격리)
- [x] `components/BrandSourceUpload.tsx` — multipart 업로드 모달 (txt/html/docx/pdf)
- [x] `components/ComplianceRiskBadge.tsx` — 차단(high)/경고(low·med)/통과 라벨 + hover popover
- [x] `components/CardPlanCard.tsx` — SPEC §14 8 항목 + 5 액션 버튼 (readOnly+pngPaths archive 모드 겸용)
- [x] `/brand-studio` — 브랜드 목록 + sources 관리 다이얼로그 (브랜드 등록은 SQL 시드 안내)
- [x] `/brand-studio/[brandId]/new` — 9 필드 폼 + ChipInput + saveCampaignInput→generatePlans 순차 + ?prefill 재생성
- [x] `/brand-studio/[brandId]/plans/[groupId]` — N variant + approve/reject + 렌더 시작(→`/jobs/{id}?return=archive`)
- [x] `/brand-studio/[brandId]/archive` — `?group=` 필수, CardArchiveItem→Plan 어댑트, PNG 경로 텍스트(다운로드 라우트는 후속 차수)
- [x] `app/layout.tsx` 헤더 nav 에 "브랜드 스튜디오" 추가
- [x] 검증: `npx tsc --noEmit` 0 errors / `npx next build` 통과 / 회귀 테스트 통과

### Phase 4.2 — 본 차수 외 (후속)
- [x] PNG 정적 다운로드 라우트 — `GET /brand-studio/cards/{group}/files/{name}` (path traversal 방어 + FileResponse) + archive 페이지 썸네일·다운로드 링크 (2026-04-29)
- [x] 브랜드 등록 UI + `POST /brands` 백엔드 — slug UNIQUE 충돌 409, Pydantic regex 422, 자동 slug 제안 + slugTouched 토글, BrandRegisterDialog (2026-04-29)
- [x] E2E smoke test 체크리스트 — `docs/brand-studio-e2e-checklist.md` (S1~S7, 알려진 한계, 회귀 발견 절차) (2026-04-29)
- [x] `brand_media_assets` 미디어 라이브러리 (CRUD) — 5 백엔드 라우트(list/upload/get/delete/download) + Pillow 이미지 검증 + width/height 자동 추출 + orientation 라벨 + Hard delete + UI graceful + BrandMediaLibrary 컴포넌트 (그리드 + 업로드 + 삭제) (2026-04-29)
  - 카드 생성 폼 ⑦ 통합은 별도 차수 (CardCampaignInput 필드 추가 + plan_generator image_asset_id 사용)
- [x] approve/reject 외 액션 PATCH (문구 수정 + 사진 교체) — `PATCH /plans/{plan_id}` (draft/reviewed 만, 자동 reviewed 전이) + `PlanEditNotAllowedError` (409) + PlanEditModal (블록별 헤드라인/부제/bullets/image_asset_id 편집 + 미디어 자산 dropdown + 썸네일 미리보기) (2026-04-29)
  - 전략 변경은 우회 deep link 유지 (재기획 = /new?prefill)
- [x] frontend 테스트 프레임워크 (vitest + Testing Library) — vitest 4.1.5 + @testing-library/react 16.3 + jsdom + @vitejs/plugin-react. vitest.config.ts(alias) + setup. 3 핵심 컴포넌트 18 테스트 (ComplianceRiskBadge × 7 / BrandRegisterDialog × 5 / CardPlanCard × 6). build-check.sh 통합 (2026-04-29)

## Phase U8: 브랜드 카드 SPEC v2.1 패치 — 결정 D1~D7 반영 (2026-04-28) ✅ 완료

> 두 문서(`SPEC-BRAND-CARD.md` v2 + `docs/brand-card-redesign.md`) 검토 후 7개 결정 위임 일괄 처리.

### 결정 D1~D7 반영
- [x] D1: brand_cards 컬럼 통합 — 신규 ALTER + 기존 점진 deprecate (SPEC §9 deprecate 매핑 표)
- [x] D2: AI 이미지 도메인 — `domain/image_generation` 재사용 (SPEC §12 [B8.5])
- [x] D3: 진입점 분리 — `generate_card_plan` + `render_card_set` 2개 (SPEC §12)
- [x] D4: 템플릿 작성 도구 — Claude `frontend-design` 스킬 (SPEC §13)
- [x] D5: reuse_guard — 차단 룰 + 사용자 override 옵션 (SPEC §5 차단 vs 경고 분리)
- [x] D6: 두 문서 단일 출처 — `docs/brand-card-redesign.md` → `docs/_archive/`
- [x] D7: redesign 통찰 SPEC promote — SEO↔카드 매트릭스(§1), 좋은 다양화(§5), 결과 화면 표시 항목(§14)

### SPEC v2.1 추가 섹션
- [x] §1 한 줄 정의 + 역할 분리 매트릭스
- [x] §5 다양화 의미 (나쁜/좋은) + 차단 vs 경고 분리
- [x] §9 brand_cards 신구 컬럼 deprecation 정책 + status 전이도
- [x] §12 진입점 2개 + AI 이미지 도메인 재사용 명시
- [x] §13 Overflow 검출 (Playwright `page.evaluate()`) + 템플릿 작성 도구
- [x] §14 결과 화면 표시 항목 8개
- [x] §16 우선순위 재정렬 (Phase 0 결정 게이트 + Phase 5 배포)
- [x] §17 수용 기준 보강 (BRAND_LENIENT 회귀, AI 이미지 가드, deploy 가이드)
- [x] §19 위험·완화 R1~R8 (R6 단가 압박 / R7 시각 과장 / R8 명명 충돌 신규)
- [x] §20 명명 규칙 (brand_card vs pattern_card 분리)

### 정리
- [x] `docs/brand-card-redesign.md` → `docs/_archive/brand-card-redesign.md` 이동
- [x] `docs/_archive/README.md` archive 정책 + 대체 문서 명시
- [x] `CLAUDE.md` 참조 문서 라인 갱신 (v2.1 + archive 위치 표기)
- [x] SPEC 본문 685 → 911 줄, 18 → 20 섹션

### 다음 단계 (Phase 1 착수 시) ✅ 모두 완료 (2026-04-29 stale 정리)
- [x] B0: SPEC v2.1 의 결정 사항을 `tasks/todo.md` 에 Phase B1~B9 체크리스트로 분해 — 본 파일 Phase B1~B9 섹션 참조
- [x] `architecture-check.sh` STAGE_ORDER `[brand_card]=0` 등록 — SPEC 의 `=2` 와 다른 의도(격리 도메인)로 채택, 결과는 동일하게 SEO 트랙과 격리됨
- [x] Phase 1 마이그레이션 + model.py + reuse_guard 골격 + plan_generator 구현 — Phase B1~B3 에서 구현 완료
- [x] Phase 1 검증 게이트: BRAND_LENIENT §7 9종 회귀 테스트 — `tests/test_compliance/test_brand_lenient_coverage.py` (32 tests, 2026-04-29 신설)

## Phase U7: 미완 항목 일괄 처리 — 보강 엣지/cannibalization 다중 author/UI 인디케이터/정렬 (2026-04-28) ✅ 완료

### body_quality_enforcer 보강 엣지 케이스 ✅
- [x] 다중 약한 섹션 — index 별 issue 누적 검증
- [x] 키워드 카운트 경계값 — 3회는 stuffing 아님 / 4회부터 stuffing
- [x] 단일 섹션 다중 issue (too_short + no_keyword 동시)
- [x] 빈 content_md
- [x] build_section_fix_prompt keyword_stuffing 분기 문구 검증
- [x] body_quality_enforcer 커버리지 → 99%

### diagnosis cannibalization 다중 author 시나리오 ✅
- [x] 같은 블로거 글 3건 Top10 → primary 는 최저 rank, same_author_count=3
- [x] self URL 이 Top10 에 있어도 same_author_others 에서 제외 (정규화 비교)
- [x] m.blog vs blog.naver.com cross-domain author 매칭
- [x] publication.url=None (draft) 진단 미발생
- [x] competing_section metric 보존 (인기글 vs VIEW 등)
- [x] diagnosis rules 커버리지 → 82%

### /rankings 정렬 옵션 ✅
- [x] `SORT_OPTIONS` 5종 — 최근 진단순/순위 좋은순/순위 나쁜순/키워드 가나다/등록일 최신
- [x] 클라이언트 sort 함수 `sortItems(items, sortBy)` — diagnosis_recent / rank_best / rank_worst / keyword_asc / registered_desc
- [x] 검색 input 옆 select 드롭다운 추가 (기본값: diagnosis_recent)

### 결과 페이지 원고 상태 5단계 인디케이터 ✅
- [x] `PublicationStatusBadge.tsx` 신규 — 5 stages: 생성 완료 / URL 미등록 / 측정 대기 / 노출 중 / 미노출 진단 필요
- [x] `determineStage()` — workflow_status + visibility_status 조합으로 판정
- [x] 색상별 dot + N/5 인디케이터 + title 툴팁 hint
- [x] `Publication` 타입에 `visibility_status`, `held_until` 옵셔널 추가
- [x] `/results/[slug]` 헤더에 통합

### 검증
- 테스트 572 → 583 (+11 — body_quality 5 + cannibalization 5 + 기존 1 갱신)
- 커버리지 70.69% → 70.82%
- frontend typecheck 통과, build-check 모두 ✓

## Phase U6: build-check 사전 실패 정리 + mypy → pyright 전환 (2026-04-28) ✅ 완료

### build-check 사전 실패 3건
- [x] `architecture-check.sh` STAGE_ORDER 에 `[diagnosis]=1` 추가 — diagnosis 가 ranking 의 후행 도메인 (target<own 룰 만족)
- [x] `tests/test_application/test_operations_home.py`, `test_ranking_bulk_check.py` ruff format
- [x] P1 묶음에서 추가된 4 파일 ruff format (storage/events_aggregator/ranking_state/republish_finalizer)

### mypy → pyright 전환
- [x] 발견: mypy strict 모드가 anthropic SDK 타입 업데이트 + Windows Python 3.13 DLL 산발 실패로 46 사전 에러 누적
- [x] `pyrightconfig.json` 신설 — basic 모드, domain/application/config 만 검사, reportUnknownXxx 무시 (점진적 강화 가능)
- [x] `.claude/hooks/build-check.sh` mypy 단계 → pyright 로 교체. 미설치 환경 SKIP 폴백
- [x] `pyproject.toml [project.optional-dependencies].dev` 에 `pyright>=1.1.400` 추가
- [x] `CLAUDE.md` 검증 규칙 섹션 갱신 (전환 사유 + mypy strict 는 선택적 수동 사용 명시)
- [x] `bash .claude/hooks/build-check.sh` ✓ build-check PASSED

## Phase U5: 외부 검토 P1 묶음 — state wiring + 테스트 + 운영 안전성 (2026-04-28) ✅ 완료

### P1-#3: 측정 루프 ↔ 상태 재계산 통합 ✅
- [x] 발견: `state_calculator` 의 `calculate_visibility_status`/`calculate_workflow_status` 가 호출자 0개 — dead code
- [x] `application/ranking_state.py` 신규 — `recalculate_visibility_after_measurement`, `sweep_workflow_transitions`, `_lookup_active_republish_job`
- [x] `ranking_orchestrator.check_rankings_for_publication` 에 visibility 재계산 통합 (snapshot 저장 직후)
- [x] `ranking_orchestrator.check_all_active_rankings` 에 workflow sweep 통합 (측정 사이클 종료 후)
- [x] `tests/test_application/test_ranking_state.py` 13 시나리오 — exposed/recovered/off_radar/no_change/not_found/hold_expired×2/job_stuck/job_failed/url_pending/active_skip/job_lookup×2

### P1-#7: events_aggregator 시나리오 테스트 ✅
- [x] `tests/test_application/test_events_aggregator.py` 8 시나리오 — empty/snapshot_only/null_captured_skip/3-way_merge/diagnosis_payload/action_metadata/same_timestamp/null_position

### P1-#6: Pretendard 로컬 폰트 전환 ✅
- [x] `web/frontend/public/fonts/PretendardVariable.woff2` 다운로드 (npm CDN 1회) — 2MB
- [x] `layout.tsx` `next/font/local` 로 전환 — `localFont({src, weight: "45 920"})`
- [x] `globals.css` @font-face CDN 제거. preconnect link 제거
- [x] `npx next build` 성공 — 모든 라우트 정상 빌드
- [x] egress 제한 환경에서도 폰트 로드 보장

### P1-#5: 마이그레이션 배포 체크리스트 ✅
- [x] `config/migrations/CHECKLIST.md` 신설 — 8섹션
- [x] 사전 준비 (백업·영향 분석·row count) / dry-run / 단계 적용 / 사후 검증 / 롤백 / 위험 명령 카탈로그
- [x] 위험 명령 카탈로그 6종 (drop cascade / not null / type / delete / truncate / mass update)
- [x] 마이그레이션 작성 가이드 5조건 (idempotent / 분리 / 검증쿼리 / 롤백SQL / 이름규칙)

## Phase U4: 외부 검토 P0 묶음 — invariant + job durability (2026-04-28) ✅ 완료

> 외부 검토(High #1·#2·Med #4) 반영. 운영 들어가기 전 데이터 부패·job 고착·탭 의미 차이 잠금.

### P0-1: publication_actions 트랜잭션 보장 ✅
- [x] `publication_actions_orchestrator._record_action` best-effort 제거 → 실패 시 raise
- [x] `republish_orchestrator._record_republished_action` 동일 적용 + 액션 기록을 부모 상태 전이 앞으로 재정렬
- [x] 회귀 테스트 변경: action insert 실패 시 status 전이 미발생 검증 (TestActionRecordIsTransactional)

### P0-2: republish_jobs 라이프사이클 finalizer ✅
- [x] `JobManager.register_on_finished` 훅 등록 메커니즘 추가, `_run_job` finally 에서 호출
- [x] `republish_orchestrator.on_pipeline_job_finished` — succeeded→completed, failed/cancelled/timed_out→failed 매핑
- [x] 실패 시 `_auto_requeue_failed_republish` — 부모 publication 자동 큐 복귀 (workflow=action_required)
- [x] `recover_stuck_republish_jobs` — 서버 재시작 시 stuck queued/running republish_jobs 일괄 회수
- [x] `web/api/main.py` lifespan 에 finalizer 등록 + 재시작 회수 호출 통합
- [x] `tests/test_application/test_republish_finalizer.py` — 13개 시나리오 (succeeded/failed/cancelled/timed_out, non-pipeline ignore, 일반 파이프라인 unrelated, recover stuck 정상/빈/부분 실패, status 검증)

### P0-3: /rankings 노출 중 탭 의미 정합성 ✅
- [x] `domain/ranking/storage.list_publications` 에 `visibility_status` IN 필터 추가
- [x] `count_publications_by_workflow_status` 에 `__exposed` 가상 키 — workflow=active AND visibility in (exposed/recovered) 카운트
- [x] `operations_home.TAB_FILTERS` 구조 변경: `{workflow, visibility}` dict. "active" 탭은 visibility=[exposed,recovered] 필터
- [x] `get_summary` "active" 카운트가 실제 노출 의미와 일치 (workflow=active AND visibility 노출)
- [x] 기존 테스트 갱신 + active=0 케이스 신규 테스트

## Phase U3: 운영 큐 UX 강화 (2026-04-27 착수)

> 사용자 결정:
> - 카드형 미사용 — 1줄 유지 + hover/클릭 popover 로 진단 근거·streak 자연어 표시
> - 우선순위 점수 생략 — 단순 정렬만
> - 보류 사유 + 재확인일 옵션 도입
> - 단가/등급(Q6) 미진행

### Q1: 1줄 행 + 진단 근거 popover ✅ 완료 (2026-04-27)
- [x] Q1.1 `application/operations_home.py` `_enrich_publication` 에 `evidence`, `metrics` 추가
- [x] Q1.2 `formatDiagnosisLines(reason, metrics)` 헬퍼 — null_streak/best_position/days_since_publish/competing_rank 등을 자연어로 변환
- [x] Q1.3 `DiagnosisBadge` 컴포넌트 — `group-hover` 로 popover 표시. 진단 헤더+신뢰도 / metrics 자연어 / evidence 리스트 / recommended_action 4섹션
- [x] Q1.4 lib/api.ts `latest_diagnosis` 타입에 `evidence: string[]`, `metrics: Record<string, unknown>` 추가

### Q3: 보류 사유 + 재확인일 옵션 ✅ 완료 (2026-04-27)
- [x] Q3.1 `HoldDialog` 사유 5종 — 이미 구현되어 있음
- [x] Q3.2 재확인일 3/7/14/직접 지정 — 이미 구현되어 있음
- [x] Q3.3 backend `held_reason` 저장·반환 — `Publication.model_dump` 가 이미 포함
- [x] Q3.4 `PublicationActionRow` 보류 표시를 자연어로 — `오늘 만료` / `내일 큐 복귀` / `N일 후 재확인` / `만료됨 — 큐 복귀 대기` + 사유 인라인

### Q2: 재발행 진행 중 잠금 ✅ 완료 (2026-04-27)
- [x] Q2.1 backend: `republishing_started_at` 컬럼 + `republish_orchestrator` 가 트리거 시 기록 — 이미 구현됨
- [x] Q2.2 `Publication.model_dump` 가 `republishing_started_at` 노출 — 이미 구현됨 (QueueItem 타입에도 존재)
- [x] Q2.3 `PublicationActionRow` 재발행 버튼 — wf="republishing" 시 비활성 `재발행 진행 중 · N분 전` + 펄스 인디케이터, title 에 정확한 시각
- [x] Q2.4 `RepublishDialog` 3종 전략 + 추천 표시 — 이미 구현됨 (full_rewrite / light / cluster, RECOMMENDED_BY_REASON 기반 자동 추천)

### Q4: 통합 타임라인 ✅ 완료 (2026-04-27)
- [x] Q4.1 `GET /rankings/publications/{id}/events?limit=N` 엔드포인트 추가 (rankings.py)
- [x] Q4.2 `application/events_aggregator.py` 신규 — 3종(snapshot/diagnosis/action) 도메인 list_* 함수 호출 후 application 레이어 merge. DB UNION 대신 도메인 격리 유지
- [x] Q4.3 `EventsTimeline.tsx` — 이벤트 행: timestamp(monospace) + type 뱃지(측정/진단/액션 색상별) + detail (위치/사유/액션). 사유는 한국어 라벨, 액션 metadata.trigger/strategy 인라인 표시
- [x] Q4.4 `/rankings/[id]` 에 `EventsTimeline` 통합 (PublicationLineage + DiagnosisCard 다음, RankingTimeline 위)

### Q5: 재발행 원고 마커 ✅ 완료 (2026-04-27)
- [x] Q5.1 frontend `Publication` 타입에 `parent_publication_id` 추가 — backend 는 model_dump 에서 이미 노출
- [x] Q5.2 `PublicationLineage` 컴포넌트 — 부모 fetch + "이 원고는 재발행 원고입니다 / 부모: ..." 배너
- [x] Q5.3 같은 keyword 의 publications 를 listPublications 로 fetch 후 부모/자식/초안 배지 + 본인 제외 형제 목록 (최대 5건 + … N건 더보기)
- [x] Q5.4 `/results/[slug]` aside 와 `/rankings/[id]` 본문에 통합. variant="results" 시 slug 가 있으면 결과 페이지로 링크

- 본 ranking 트랙은 SPEC-SEO-TEXT.md / SPEC-BRAND-CARD.md 어느 쪽에도 정의 없음. **별도 SPEC-RANKING.md 신규 작성 필요 여부는 사용자 결정 사항** — Phase R1 착수 전 확인. 미작성 시 `tasks/todo.md` 본 섹션이 사실상 SPEC 역할
- SPEC v2 범위 변경 ❌ — 기존 8단계 파이프라인은 손대지 않음
- 변경 이력 기록 대상: 루트 `CLAUDE.md` "변경 이력" 섹션에 `2026-04-24: 순위 추적 도메인(ranking) 추가, APScheduler in-process 통합` 1줄 추가 (Phase R7 단계에서)

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

## 📦 Phase B1~B6 — Batch Pipeline MVP (Phase 1, 3~4일 예상)

### B1 — Supabase 마이그레이션 + 도메인 모델

- [ ] B1.1 `config/schema.sql` 끝에 `keyword_batches` 테이블 SQL 추가 (SPEC-BATCH §4)
- [ ] B1.2 같은 파일에 `keyword_batch_items` 테이블 SQL 추가 + 인덱스 4개
- [ ] B1.3 Supabase 대시보드 SQL Editor 에 적용 + `select count(*) from keyword_batch_items` 확인 (둘 다 0)
- [ ] B1.4 `domain/batch/__init__.py` + `model.py` (Pydantic: `KeywordBatch`, `KeywordBatchItem`, `BatchEnqueueResult`)
- [ ] B1.5 `domain/batch/csv_parser.py` — CSV → list[KeywordBatchItem] 변환 + 검증 (필수 컬럼 누락, 중복 키워드, 형식 오류 분류)
- [ ] B1.6 `domain/batch/storage.py` — Supabase CRUD (`insert_batch`, `insert_items`, `get_batch`, `list_items`, `update_item_status`, `update_item_result`)
- [ ] B1.7 `domain/batch/CLAUDE.md` — 격리 규칙, 30/300줄, Pydantic 반환
- [ ] B1.8 `architecture-check.sh` 의 `STAGE_ORDER` 에 `[batch]=0` 추가
- [ ] B1.9 `tests/test_batch/test_csv_parser.py` (5건+) + `tests/test_batch/test_storage.py` (mock 기반 5건+)

### B2 — Application: BatchJobManager + Orchestrator

- [ ] B2.1 `application/batch_job_manager.py` — `JobManager` 패턴 참고 + 별도 thread pool. `BATCH_MAX_WORKERS` env 로딩
- [ ] B2.2 `application/batch_orchestrator.py`:
  - `enqueue_from_csv(csv_path, mode, ...) -> BatchEnqueueResult`
  - `dispatch_item(item_id) -> None` (operation 분기 → `run_analyze_only/run_generate_only/run_pipeline`)
  - `retry_item(item_id) -> None` (max_retries 체크)
  - `cancel_batch(batch_id) -> int` (남은 queued 개수 반환)
- [ ] B2.3 mode 검증: `now` 만 200, `overnight`/`auto` 는 `NotSupportedYetError` raise (router 가 400)
- [ ] B2.4 `domain/crawler/brightdata_client.py` 에 module-level `Semaphore` 추가 — semaphore.acquire/release 가 `_fetch_with_retry` 진입/종료에 감김. **단일 프로세스 안전망** 주석 명시
- [ ] B2.5 `tests/test_application/test_batch_orchestrator.py` (10건+) — operation 분기 / retry / cancel / NotSupportedYet
- [ ] B2.6 `tests/test_application/test_batch_job_manager.py` (5건+) — worker 큐 동작, MAX_WORKERS 한도, exception isolation

### B3 — Web API + WebSocket 진행 보고

- [ ] B3.1 `web/api/routers/batches.py`:
  - `POST /batches` — multipart CSV 또는 JSON. mode=now 만 200, 그 외 400
  - `GET /batches?limit=20`
  - `GET /batches/{id}`
  - `GET /batches/{id}/items?status=...&limit=...`
  - `POST /batches/{id}/cancel`
  - `POST /batches/{id}/items/{item_id}/retry`
- [ ] B3.2 `web/api/main.py` 에 router 등록 (lifespan 변경 없음)
- [ ] B3.3 X-API-Key 인증 (`require_api_key` Depends 사용)
- [ ] B3.4 `tests/test_web/test_batches_api.py` (8건+) — 인증/모드 검증/CSV 파싱/cancel/retry

### B4 — CLI

- [ ] B4.1 `scripts/run_batch.py` — argparse:
  - `--csv <path>` `--mode now` `--max-workers N` `--name "..."`
  - `--status <batch_id>`
  - `--retry-item <item_id>`
- [ ] B4.2 BatchEnqueueResult 를 사람이 읽기 좋게 출력 (created N / skipped M / failed K + error 샘플)
- [ ] B4.3 `--status` 는 batch + 진행 요약 + 최근 5 실패 item 표시

### B5 — Frontend (Next.js)

- [ ] B5.1 `web/frontend/src/lib/api.ts` 에 `createBatch`, `listBatches`, `getBatch`, `getBatchItems`, `cancelBatch`, `retryBatchItem` 6 함수 추가
- [ ] B5.2 `BatchUploadForm.tsx` — CSV file input + textarea(붙여넣기) + mode 라디오 (now 만 활성, overnight/auto 는 disabled + tooltip "Phase 3 예정") + operation default `analyze`
- [ ] B5.3 `BatchProgressTable.tsx` — 5초 poll 로 batch 상태 + 카운터 (succeeded/failed/skipped/needs_review) 갱신
- [ ] B5.4 `app/batches/page.tsx` — 배치 목록 (recent 20)
- [ ] B5.5 `app/batches/[id]/page.tsx` — 단건 dashboard (BatchProgressTable + item 리스트 + 일괄 액션)
- [ ] B5.6 navigation 에 "배치" 탭 추가

### B6 — 검증 + 문서

- [ ] B6.1 단일 흐름 보호 체크리스트 (SPEC-BATCH §8) 모두 그린
  - `tests/test_application/test_orchestrator.py` 그린
  - `python scripts/run_pipeline.py --keyword "테스트키워드"` smoke pass
  - 단일 `POST /api/jobs` 응답 시간 회귀 없음
- [ ] B6.2 `bash .claude/hooks/build-check.sh` 그린 (ruff/format/architecture/pyright/pytest 0 에러)
- [ ] B6.3 `architecture-check.sh` 가 `domain/batch → 다른 도메인` 차단 검증
- [ ] B6.4 운영 smoke — CSV 5건 (`tests/fixtures/batch/keywords_5.csv`) → 즉시 모드 → 5건 모두 succeeded 또는 needs_review 까지 도달
- [ ] B6.5 운영 smoke 100건 (별도 fixture, opt-in) — 6~8h 안에 완주 + 단일 호출 영향 0
- [ ] B6.6 `tasks/lessons.md` 에 "Phase 1 BatchJobManager + semaphore 운영 패턴" 기록
- [ ] B6.7 루트 `CLAUDE.md` "변경 이력" 1줄 추가 — `2026-05-04: 키워드 배치 운영 시스템 (Batch Pipeline) Phase 1 추가`

---

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

## 🔗 Phase B7 — FK 회수 + PatternCard 보관함 (Phase 2 PR1, 2026-05-04 착수)

> SPEC-BATCH §3 Phase 2 의 첫 갈래. batch 로 처리한 키워드도 단일 진입과 동일한 운영 워크플로우(보관함 노출 → URL 등록 → 순위 추적)에 자연스럽게 진입. 사전 필터·클러스터 재사용·검수 큐는 PR2 로 분리.

### B7.1 도메인 — id 회수 ✅
- [x] `domain/analysis/pattern_card.py` — `_save_to_supabase` 가 `str | None` 반환, `save_pattern_card` 가 `(Path, str | None)` tuple 반환. `_extract_inserted_id` 헬퍼 추가
- [x] `domain/batch/storage.py` — `update_item_result` 신규 함수 (partial update + 모든 None 시 noop)

### B7.2 application — id 전파 ✅
- [x] `application/models.py` — `AnalyzeResult.pattern_card_id`, `GenerateResult.pattern_card_id`+`generated_content_id`, `PipelineResult.pattern_card_id`+`generated_content_id` (모두 nullable, default None)
- [x] `application/stage_runner.py` — `run_stage_cross_analysis` tuple 반환, `_save_generated_to_supabase` tuple 반환, `ComposeStageResult` NamedTuple 도입
- [x] `application/orchestrator.py` — id propagation (시그니처 무변경)
- [x] `application/batch_orchestrator.py` — `_run_operation` 의 3 분기에서 id 캡처 + `_record_item_result` 헬퍼 (graceful try/except)

### B7.3 Web API ✅
- [x] `web/api/routers/pattern_cards.py` 신규 — `GET /pattern-cards/recent` / `by-id/{id}` / `by-slug/{slug}/latest`
- [x] `web/api/main.py` — pattern_cards router include
- [x] `web/api/routers/batches.py` — `list_batch_items` 응답에 `keyword_slug` enrich (backend `_slugify` 단일 출처)

### B7.4 Frontend ✅
- [x] `web/frontend/src/lib/api.ts` — `PatternCardSummary`/`Detail` 타입 + `listRecentPatternCards`/`getPatternCardById`/`getPatternCardBySlugLatest` 함수 + `BatchItem.keyword_slug` 필드
- [x] `web/frontend/src/app/patterns/by-id/[id]/page.tsx` 신규 — 분석 카드 그리드 (target_reader, sections, dia_plus, image_pattern, appeal_points, related_keywords, distributions)
- [x] `web/frontend/src/components/BatchProgressTable.tsx` — `결과` 컬럼 추가 + `ResultLinks` inner component (analyze→패턴 / generate→결과 / pipeline→둘 다, id None 시 placeholder + tooltip)

### B7.5 테스트 ✅ — 108 passed
- [x] `tests/test_analysis/test_pattern_card.py` — `save_pattern_card` tuple / `_extract_inserted_id` / `_save_to_supabase` mock 8 케이스
- [x] `tests/test_batch/test_storage.py` — `update_item_result` partial / noop / Supabase raise
- [x] `tests/test_application/test_stage_runner.py` — `run_stage_cross_analysis` tuple / `run_stage_compose` ComposeStageResult
- [x] `tests/test_application/test_orchestrator.py` — `PipelineResult` 두 id propagation 검증
- [x] `tests/test_application/test_batch_orchestrator.py` — analyze/generate/pipeline × (id 회수 / 모두 None / update 실패) 검증
- [x] `tests/test_application/test_pr1_id_propagation.py` 신규 — 단일 흐름이 batch storage 호출 안 함 (cross-coupling 0)
- [x] `tests/test_web/test_pattern_cards_router.py` 신규 — recent/by-id/by-slug × (200 / 404 / 503 table missing)
- [x] `tests/test_web/test_batches_api.py` — `keyword_slug` enrich 검증

### B7.6 문서 + 검증 ✅
- [x] `bash .claude/hooks/build-check.sh` 그린 — 1136 passed, 76.45% coverage
- [x] `cd web/frontend && npx tsc --noEmit && npx next build` 그린
- [x] commit `feat(batch): Phase 2 PR1 — FK 회수 + PatternCard 보관함` (`2582d72`)

---

## 🧮 Phase B8 — 사전 필터 + 클러스터 재사용 (Phase 2 PR2, 2026-05-04 착수)

> SPEC-BATCH §3 Phase 2 의 두 번째 갈래. batch 입력 압축 ("100→30~50"). 검수 큐·triple link 사후 백필은 PR3·PR4 로 분리. cluster_dedupe **default OFF** (1페이지 노출 리스크 보수 처리).

### B8.1 도메인 — settings + storage ✅
- [x] `config/settings.py` — `batch_cluster_primary_timeout_sec=600`, `batch_cluster_poll_interval_sec=1.0`
- [x] `domain/batch/storage.py` — `update_item_result` 인자에 `search_volume`/`difficulty_grade` 추가 + `find_primary_in_cluster(batch_id, cluster_id)` 신규

### B8.2 application — 사전 필터 + 클러스터 헬퍼 ✅
- [x] `application/batch_orchestrator.py`:
  - `_has_prefilter(batch)` — 임계값 설정 여부
  - `_apply_prefilter(item, batch)` — analyze_keyword 호출 + 임계값 검사 + skipped 마킹 (graceful)
  - `_exceeds_difficulty(grade, max_grade)` — DifficultyGrade 우선순위 dict 비교
  - `_record_prefilter_meta` — search_volume/difficulty_grade 메타 graceful 저장
  - `_resolve_cluster_primary` — primary polling/timeout/폴백 정책
  - `_run_member_with_primary` — operation 별 재사용 분기 (analyze=즉시 / generate·pipeline=pattern_card_path 주입)
  - `_resolve_primary_card_path` — pattern_cards 테이블 lookup → output_path/임시파일 폴백
  - `_dispatch_item` 흐름 변경: batch fetch → 사전 필터 → cluster 재사용 → operation 분기
- [x] `enqueue_from_csv` 인자 확장: `min_search_volume`/`max_difficulty`/`cluster_dedupe=False`

### B8.3 Web API + CLI ✅
- [x] `web/api/routers/batches.py` — `BatchCreateJsonRequest` + multipart form 에 임계값/cluster_dedupe (default False)
- [x] `_form_int`/`_form_bool` 헬퍼 신규
- [x] `scripts/run_batch.py` — `--min-search-volume` / `--max-difficulty` / `--cluster-dedupe` 옵션

### B8.4 Frontend ✅
- [x] `web/frontend/src/lib/api.ts` — `createBatch`/`createBatchFile` 타입에 임계값·cluster_dedupe 추가
- [x] `web/frontend/src/components/BatchUploadForm.tsx` — 최소 월 검색량 input + 최대 난이도 select + 클러스터 재사용 checkbox (default OFF + inline 도움말)

### B8.5 테스트 ✅ — 70 passed
- [x] `tests/test_batch/test_storage.py` — find_primary_in_cluster 발견/부재, update_item_result 메타 인자
- [x] `tests/test_application/test_batch_orchestrator.py` — storage_mock fixture 에 get_batch default 보강
- [x] `tests/test_application/test_batch_prefilter.py` 신규 — 임계값 6 케이스 + graceful pass
- [x] `tests/test_application/test_batch_cluster.py` 신규 — primary 부재/terminal/succeeded/polling/timeout, member analyze/generate/pipeline 분기
- [x] `tests/test_web/test_batches_api.py` — JSON/multipart 임계값 전달 + cluster_dedupe default OFF

### B8.6 문서
- [ ] `SPEC-BATCH.md` — 변경 이력 + "클러스터 재사용 사용 가이드" 신규 절
- [ ] `CLAUDE.md` 변경 이력 1줄
- [ ] `domain/batch/CLAUDE.md` — find_primary_in_cluster + cluster_dedupe default OFF 명시

### B8.7 검증 + commit ✅
- [x] `bash .claude/hooks/build-check.sh` 그린 — 1160 passed, 76.51% coverage
- [x] `cd web/frontend && npx tsc --noEmit && npx next build` 그린
- [x] commit `feat(batch): Phase 2 PR2 — 사전 필터 + 클러스터 재사용` (`59a5f86`)

---

## 🩺 Phase B9 — 검수 큐 (Phase 2 PR3, 2026-05-04 착수)

> SPEC-BATCH §3 Phase 2 의 세 번째 갈래. **운영 철학**: 후보 키워드는 모두 발행 대상. needs_review 는 폐기 X — 발행 전 확인/수정 대기. 핵심 액션: approve / needs_fix. reject 는 예외 (UI dropdown 보조). status 머신: succeeded → ready_to_publish 의미 분리.

### B9.1 도메인 — model + storage ✅
- [x] `domain/batch/model.py` — `ItemStatus` Literal 에 `"ready_to_publish"` 추가, `KeywordBatch.ready_to_publish_count` Pydantic 필드 (DB 미반영)
- [x] `domain/batch/storage.py` — `count_items_by_status` 의 dict 에 `ready_to_publish_count` 추가 + `update_batch_status` payload 에서 ready_to_publish_count 제외 (DB 컬럼 없음)
- [x] `update_item_review(item_id, *, review_status, status=None, reviewer=None)` 신규 — approve 시 status 동시 전환
- [x] `list_review_pending_items(batch_id, limit=200)` 신규 — `status='needs_review' AND review_status='pending'`

### B9.2 application — 자동 마킹 ✅
- [x] `_run_operation` / `_run_member_with_primary` 가 `compliance_passed: bool | None` 반환
- [x] `application/models.py` — `PipelineResult.compliance_passed` 필드 추가
- [x] `application/orchestrator.py:run_pipeline` — PipelineResult.compliance_passed 채움
- [x] `_dispatch_item` final status 분기:
  - analyze → `succeeded` (분석만)
  - generate/pipeline + compliance_passed=True → `ready_to_publish`
  - generate/pipeline + compliance_passed=False/None → `needs_review` (안전망)

### B9.3 Web API ✅
- [x] `GET /batches/{id}/review` — list_review_pending_items + keyword_slug enrich
- [x] `POST /batches/{id}/items/{item_id}/review` — approve→ready_to_publish, needs_fix, reject. ReviewActionRequest 본문, invalid action 400

### B9.4 Frontend ✅
- [x] `web/frontend/src/lib/api.ts` — `BatchSummary.ready_to_publish_count` + ReviewAction + listReviewQueue / reviewItem
- [x] `web/frontend/src/app/batches/[id]/review/page.tsx` 신규 (Next 16 use(params))
- [x] `web/frontend/src/components/BatchReviewQueue.tsx` 신규 — 폴링 5초, 액션 ApproveAction (승인 / 수정필요 / 거부 dropdown)
- [x] `BatchProgressTable` counters 라벨 정정 ("발행 준비"/"분석 완료") + 검수 큐 link + StatusBadge ready_to_publish

### B9.5 테스트 ✅ — 68 passed (storage 5 + orchestrator 3 + API 5 + 기존 회귀)
- [x] `tests/test_batch/test_storage.py` — update_item_review 3 / list_review_pending_items 2 / count ready_to_publish_count 1
- [x] `tests/test_application/test_batch_orchestrator.py` — generate/pipeline 의 compliance_passed True/False/None 분기 + 기존 회귀
- [x] `tests/test_web/test_batches_api.py` — review queue 5 케이스 + GET /batches/{id} ready_to_publish_count 응답 검증

### B9.6 검증 + commit ✅
- [x] `bash .claude/hooks/build-check.sh` 그린
- [x] `cd web/frontend && npx tsc --noEmit && npx next build` 그린 — `/batches/[id]/review` 라우트 등록
- [x] commit `feat(batch): add review queue and ready-to-publish state` (`042c90c`)

---

## 🛠️ Phase B10 — Triple Link 사후 백필 (Phase 2 PR4, 2026-05-04 착수)

> SPEC-BATCH §3 Phase 2 의 마지막 갈래 — fire-and-forget 회수 실패 사후 보강 운영 도구. 자동 cron 미사용. 운영자가 명시적으로 호출 (CLI / Web API). idempotent.

### B10.1 도메인 + application ✅
- [x] `domain/batch/storage.py` — `find_pattern_card_by_triple(slug, keyword)` 신규 (slug+keyword ORDER BY created_at DESC LIMIT 1) + `find_generated_content_by_triple(job_id, slug, keyword)` 신규 (job_id 1차 + slug+keyword 2차 fallback, **job_id None 시 1차 스킵**)
- [x] `application/batch_orchestrator.py:backfill_unlinked_items(batch_id)` 신규 — list_items 순회 + idempotent (이미 채워진 FK skip) + matched/still_unlinked 카운트 반환

### B10.2 Web API + CLI ✅
- [x] `POST /batches/{id}/backfill-fk` — 동기 응답
- [x] `scripts/run_batch.py --backfill-fk BATCH_ID` 옵션 + `_backfill` 헬퍼

### B10.3 테스트 ✅ — storage 5 + orchestrator 4 + API 1
- [x] `find_pattern_card_by_triple` 발견/부재
- [x] `find_generated_content_by_triple` primary match / fallback / job_id None 1차 스킵 / 부재
- [x] `backfill_unlinked_items` 양쪽 매칭 / pattern_card 만 / 부재 / idempotent
- [x] `POST /backfill-fk` 응답 검증

### B10.4 검증 + commit
- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] commit `feat(batch): add triple-link FK backfill tool` (Phase 2 PR4)

---

## ⚙️ Phase B15 — Worker process 분리 (Phase 3 PR2, 2026-05-05 착수)

> SPEC-BATCH §3 Phase 3 PR2. PR1 의 `dispatch_overnight_batches()` 골격 위에 (1) 멀티 워커 race-safe atomic claim, (2) 외부 cron 친화 시간대 게이트를 더해 web process + 외부 cron 동시 운영을 가능하게 한다. Anthropic Batch API 는 Phase 5+ 별도 PR (운영 데이터 누적 후 trade-off 판단).

### B15.1 도메인 — atomic claim ✅
- [x] `domain/batch/storage.claim_item_for_dispatch(item_id, *, job_id)` 신규 — PostgREST `eq("status","queued")` 필터로 race-safe queued→running. 두 worker 동시 호출 시 한쪽만 1 row 받고 다른 쪽은 0 row → None 반환

### B15.2 application — atomic claim 적용 ✅
- [x] `application/batch_orchestrator._dispatch_item` — 기존 `update_item_status("running", job_id, started_at)` 패턴을 `claim_item_for_dispatch` 호출로 교체. claim 실패 시 즉시 return (run_* 호출 0)

### B15.3 settings + CLI 시간대 게이트 ✅
- [x] `config/settings.py` — `batch_overnight_hour_kst` (default 22) + `batch_overnight_force` (default False) Field 추가
- [x] `scripts/run_batch.py` — `_is_overnight_window(*, batch_id)` 신규 + `_dispatch_overnight` 가 게이트 미통과 시 noop (exit 0). batch_id 명시 또는 force=true 시 우회

### B15.4 테스트 ✅
- [x] `tests/test_batch/test_storage.py` — claim 성공 (KeywordBatchItem 반환 + payload 검증) / 이미 잡힘 (None)
- [x] `tests/test_application/test_batch_orchestrator.py` — `storage_mock` fixture 가 claim_item_for_dispatch default 를 get_item.return_value 로 설정 + `test_claim_failed_skips_dispatch` (claim None → run_* 0). 기존 `test_analyze_operation_calls_run_analyze_only` 의 'running' status assertion 을 atomic claim 의미에 맞게 정정 (claim_item_for_dispatch.assert_called_once())
- [x] `tests/test_scripts/test_run_batch_overnight_gate.py` — 4 케이스: batch_id bypass / force bypass / window match / window miss

### B15.5 검증 + commit
- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] commit `feat(batch): Phase 3 PR2 — atomic claim + cron overnight 시간대 게이트`

---

## 🔔 Phase B16 — 알림 인프라 (Phase 4 PR1, 2026-05-05 착수)

> SPEC-BATCH §3 Phase 4 PR1. webhook 미설정 시 noop, 실패 graceful 의 env-driven 인프라. 운영 중요 사건 (의료법 위반 / 배치 완료 / 배치 전체 실패 / 야간 dispatch) 을 운영자에게 알린다.

### B16.1 application — notifier 모듈 ✅
- [x] `application/notifier.py` — Slack webhook. `send_text` / `send_batch_completed` / `send_batch_failed` / `send_compliance_violation` / `send_overnight_dispatched`. webhook URL 미설정 → 모든 함수 즉시 noop. requests.post 5초 timeout, 실패 graceful (logger.warning)

### B16.2 batch_orchestrator hook 적용 ✅
- [x] `_dispatch_item` final status 분기 직후: `compliance_passed is False AND operation in (generate, pipeline)` 시 `send_compliance_violation` 호출
- [x] `recompute_batch_status`: queued/running → completed 첫 전이 시 1회. failed_count == total_count → `send_batch_failed`, 그 외 → `send_batch_completed` (counters + estimated_cost_usd)
- [x] `dispatch_overnight_batches`: dispatched_items > 0 시 `send_overnight_dispatched(batches, items)`
- [x] `_run_operation` / `_run_member_with_primary` 반환을 `tuple[bool | None, list[str]]` 로 확장 — 위반 카테고리 전파
- [x] 모든 알림 호출은 try/except 흡수 — slack 다운이 본 흐름 차단 X

### B16.3 settings + 토글 ✅
- [x] `config/settings.py` — `slack_webhook_url` (default None), `slack_notify_compliance_violations` (default False — 검수 큐 외 추가 알림 필요할 때만 활성)

### B16.4 테스트 ✅ — 13건
- [x] `tests/test_application/test_notifier.py` — 10 케이스 (webhook 미설정 noop / 호출 시 payload / 예외 graceful / 4xx 흡수 / batch_completed counters / batch_failed reason / compliance toggle off / categories / overnight zero items / overnight counts)
- [x] `tests/test_application/test_batch_orchestrator.py` 추가 — recompute 4 (completed first / 이미 completed 중복 방지 / 전체 실패 / notifier 실패 graceful) + _dispatch_item 4 (violation triggers / passed=True 0 / None 0 / analyze 0) + overnight 1

### B16.5 검증 + commit
- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] commit `feat(batch): Phase 4 PR1 — 알림 인프라 (Slack webhook)`

---

## 📤 Phase B17 — publication 자동 등록 (Phase 4 PR2, 2026-05-05 착수)

> SPEC-BATCH §3 Phase 4 PR2. 운영 철학 §0 — 후보 키워드 모두 발행 대상이지만 **실제 발행은 운영자가 네이버 블로그 직접 수행**. publications 등록도 명시적 opt-in (`KeywordBatch.auto_publish_enabled` default False).

### B17.1 application — auto_publisher use case ✅
- [x] `application/auto_publisher.py` 신규. `auto_publish_ready_items(batch_id)` — `auto_publish_enabled=False` 즉시 noop (`skipped_reason="auto_publish_disabled"`). ready_to_publish + target_url 채워진 item 을 `ranking_orchestrator.register_publication` 호출 (멱등 + `_attach_batch_item` 가 publication_id 자동 백필). target_url 부재 → skipped("no_target_url"), 이미 publication_id 있음 → skipped("already_linked"), URL 형식 오류 → failed

### B17.2 자동 트리거 + CLI/API ✅
- [x] `recompute_batch_status` — completed 첫 진입 + `batch.auto_publish_enabled=True` 시 `auto_publisher.auto_publish_ready_items` 자동 호출 (graceful, 실패해도 batch status 영향 X)
- [x] CLI: `scripts/run_batch.py --auto-publish <batch_id>` (`_auto_publish` 헬퍼). disabled 케이스는 친화 메시지 + exit 0
- [x] Web API: `POST /batches/{id}/auto-publish` — 응답에 batch_id + 카운트 + items 상세
- [x] frontend `web/frontend/src/lib/api.ts` — `autoPublishBatch(batchId)` 함수 + `AutoPublishItemResult` 타입

### B17.3 테스트 ✅ — 8 + 4 + 3 = 15건
- [x] `tests/test_application/test_auto_publisher.py` — 8 케이스 (disabled / missing batch / no_target_url / already_linked / register 호출 / ValueError fail / unexpected exception 흡수 / mixed mix 집계)
- [x] `tests/test_application/test_batch_orchestrator.py` 추가 — 4 케이스 (auto_publish triggered on completion / disabled 시 미호출 / 실패 graceful / 이미 completed 중복 방지)
- [x] `tests/test_web/test_batches_api.py` 추가 — 3 케이스 (registered counts / disabled skipped_reason / missing 404)

### B17.4 검증 + commit
- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] commit `feat(batch): Phase 4 PR2 — publication 자동 등록 (opt-in)`
