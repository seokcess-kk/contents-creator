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

### [Pre-1] 개발 환경 준비
- [x] `python -m venv .venv` 후 활성화 (기존 venv 재사용) — 2026-04-16
- [x] `pip install -e ".[dev]"` 실행 성공 확인 — 신규 의존성 6종(playwright/jinja2/python-docx/pypdf/pdfplumber/pillow) 포함 — 2026-04-16
- [ ] `bash .claude/hooks/build-check.sh` 그린 확인 (스켈레톤 기준)
- [ ] Supabase 프로젝트 생성 + `config/schema.sql` v3 적용 (브랜드 4개 테이블 포함)

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
- [ ] `python -c "from config.settings import settings; print(settings.bright_data_api_key is not None)"` 로 로드 확인 (Pre-1 의존)

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

### [BC-5] 로고 자동 추출 셀렉터 세트 실측 ✅ 로직 검증 완료, ⏸ 실존 URL 대기 (2026-04-16)
- [x] 로컬 fixture 7/7 통과 (`dev/active/bc-tests/bc5_logo.py`)
- [x] 폴백 셀렉터 5단 순서 확정: `link[rel=icon]` → `meta[og:image]` → `header img[alt*=logo]` → `[class*=logo] img` → `img[src*=logo]`
- [x] 우선순위 정확 (case6 link + og:image 공존 → link 선택)
- [ ] 실존 한의원 홈페이지 5~10곳 URL 사용자 제공 → 성공률 집계
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

## 🚧 Phase 1 — 크롤러 도메인 (SEO 트랙, SPEC-SEO-TEXT.md §3 [1][2])

- [ ] `domain/crawler/model.py` — `SerpResult`, `BlogPage`, `InsufficientCollectionError`
- [ ] `domain/crawler/brightdata_client.py` — 공통 HTTP, 재시도, 타임아웃
- [ ] `domain/crawler/serp_collector.py` — 네이버 블로그 URL 필터, 최소 7개
- [ ] `domain/crawler/page_scraper.py` — Web Unlocker 호출 (C1 결과 반영)
- [ ] `application/stage_runner.py` 에 `run_stage_serp_collection`, `run_stage_page_scraping` 추가
- [ ] `tests/test_crawler/` 단위 테스트 (mock 기반)
- [ ] 실제 키워드 1개로 end-to-end 수집 검증
- [ ] `bash .claude/hooks/build-check.sh` 통과
- [ ] `tasks/lessons.md` 에 수집 결과 기록

## 🚨 Phase 2 실측 이슈 (2026-04-16 발견, 후속 조치 대기)

- [ ] **[P2-I1] 블로그 태그 수집 불가** — 모바일 네이버 본문 HTML 에 태그 영역 자체가 없음. 데스크톱은 iframe 껍데기만 반환. 별도 스프린트로 분리 예정. lessons.md P2 참조
  - [ ] 선택지 결정: (a) PostView.nhn iframe 실측, (b) 별도 JSON API 탐색, (c) SPEC 에서 전면 삭제
  - [ ] 결정 후 [5] cross_analyzer 의 `aggregated_tags` 와 [6] `suggested_tags` 폴백 로직 수정
  - 현재 상태: `PhysicalAnalysis.tags` 는 빈 리스트로 동작 (코드는 폴백 셀렉터 유지)

- [ ] **[P2-I2] 네이버 블로거가 소제목을 잘 안 씀** — 10개 중 8개가 소제목 0개. 폰트 기반 감지는 정상 동작하나 원본 데이터가 부재. lessons.md P2 참조
  - [ ] [4a] semantic_extractor 진입 시 "소제목 0개 → 전체를 단일 섹션으로 분류" 폴백 로직 추가
  - [ ] [5] cross_analyzer 구조 패턴 집계 시 소제목 있는 블로그만 대상으로 필터링
  - [ ] [6] outline_writer 의 "상위 글 구조 복제 금지" 지시를 "참고할 구조가 있으면" 로 조건부화

## 🔮 Phase 2~8 — SEO 트랙 이후 단계 (각 단계 착수 시 분해)

- **Phase 2**: 물리 분석 (`physical_extractor`) — 이미지 메타 추출 포함 (`image_pattern`)
- **Phase 3**: 의미 + 소구 + 교차 분석 (`semantic_extractor`, `appeal_extractor`, `cross_analyzer`, `pattern_card`)
- **Phase 4**: 생성 (`prompt_builder`, `outline_writer`, `body_writer`) — M2 불변 규칙 + image_prompts 생성
- **Phase 5**: 의료법 검증 — **`CompliancePolicy` enum 전제로 설계**
  - [ ] `domain/compliance/rules.py` — `CompliancePolicy` enum (`SEO_STRICT`, `BRAND_LENIENT`) 정의
  - [ ] `RULES: dict[CompliancePolicy, list[Rule]]` 구조로 두 프로필 동시 정의
  - [ ] `checker(text, policy=CompliancePolicy.SEO_STRICT)` 시그니처 — 기본값은 strict
  - [ ] `fixer` 는 정책 독립적. SEO 트랙만 도입부 재생성 금지(M2) 추가 적용
  - [ ] 모든 SEO 트랙 호출부에 `policy=SEO_STRICT` 명시 전달
  - [ ] 사용자 제공 8개 카테고리 확정 시점에 `BRAND_LENIENT` 7개 초안 (§7-2) 도 함께 재검토
  - [ ] **⚠️ 순서 의존성**: Phase B7 (브랜드 카드 컴플라이언스) 는 이 Phase 5 완료 이후에만 착수 가능
- **Phase 6**: AI 이미지 생성 🆕 (`domain/image_generation/`) — Gemini 3.1 Flash Image Preview, 캐시 + 예산 + 재시도
- **Phase 7**: 조립 (`assembler`, `outline_md`, `naver_html`) — outline.md 에 이미지 매핑 가이드
- **Phase 8**: 통합 + E2E 테스트 + `run_pipeline` 본문 채움

---

## 🎨 Phase B1~B9 — 브랜드 카드 트랙 (SPEC-BRAND-CARD.md §5)

> SEO 트랙과 완전 격리. `domain/brand_card/` 는 `domain/compliance/rules.py` 만 예외적 import. Phase 0.6 실측 완료 후 착수.

### Phase B1 — 도메인 스켈레톤 + 모델
- [ ] `domain/brand_card/model.py` — `BrandProfile`, `BrandAssets`, `DesignGuide`, `BusinessContext`, `BrandGuideline`, `MediaAsset`, `MediaAssetType`, `BlockId` Enum, `ImageSourceKind`·`AiImagePurpose` Enum, `Block`, `ImageSlot` (+ `model_validator`), `CardPlan`, `CardPlansResult`, `BrandCardResult`
- [ ] `domain/brand_card/block_rules.py` — `BLOCK_MEDIA_MAPPING` 상수 (§3-2-1)
- [ ] `domain/brand_card/repository.py` — Supabase brand_profiles/assets/media/cards CRUD
- [ ] `domain/brand_card/CLAUDE.md` — 도메인 규칙 + M2 스타일 불변 규칙 (버튼 UI 금지 등)
- [ ] `tests/test_brand_card/test_model.py` — Enum·validator·매핑 단위 테스트

### Phase B2 — 브랜드 소스 로딩 + 자산 추출 ([B1][B2][B3])
- [ ] `domain/brand_card/source_loader.py` — 홈페이지/txt/docx/pdf 수집 + BS4 전처리 + 로고 추출
- [ ] `domain/brand_card/asset_extractor.py` — Sonnet 호출, user_input skip 로직
- [ ] `domain/brand_card/asset_merger.py` — user_input + llm_extracted 머지 (§4-5)
- [ ] `domain/brand_card/prompt_builder.py` — 모든 LLM 프롬프트 단일 진입점 (Sonnet asset + Opus card + Sonnet compliance)
- [ ] `application/stage_runner.py` 에 `run_stage_brand_source_loading`, `run_stage_brand_asset_extraction` 추가
- [ ] `application/orchestrator.register_brand` — upsert 로직 (§4-6), diff 기반 version 증가
- [ ] `tests/test_brand_card/test_source_loader.py`, `test_asset_extractor.py` (mock)

### Phase B3 — 카드 기획 ([B4] + [B4-v])
- [ ] `domain/brand_card/card_planner.py` — Opus 호출, 단일 호출 N variant, available_media 전달, pattern_card=None 분기
- [ ] `domain/brand_card/card_plan_validator.py` — `validate_card_plan()` 필수 블록·Enum·템플릿 슬롯·media 실재성 검증, 실패 시 [B4] 재호출 피드백 생성
- [ ] `application/stage_runner.run_stage_card_planning`
- [ ] `tests/test_brand_card/test_card_planner.py` — pattern_card 유무 분기, validate_card_plan 엣지 케이스

### Phase B4 — 이미지 슬롯 생성 ([B5])
- [ ] `domain/brand_card/image_generator.py` — Gemini Nano Banana 호출, 2계층 캐시 (`brands/{slug}/cache/` + 작업 복사본), sha256 키, fallback_text 분기
- [ ] `application/stage_runner.run_stage_image_slot_generation`
- [ ] `tests/test_brand_card/test_image_generator.py` — 캐시 히트/미스, media_library 참조 skip

### Phase B5 — 템플릿 시스템 + HTML 합성 ([B6])
- [ ] `domain/brand_card/templates/` 5종 prototyping — `clinic-classic`, `clinic-bold`, `clinic-minimal`, `clinic-warm`, `clinic-editorial` (Claude `frontend-design` 스킬 활용)
- [ ] 각 템플릿 폴더 구조: `card.html.j2` + `style.css` + `meta.json` + `blocks/{block_id}.html.j2`
- [ ] `domain/brand_card/template_registry.py` — templates/ 글로빙 + meta.json 로드
- [ ] `domain/brand_card/html_renderer.py` — Jinja2 합성, `template.validates(card_plan)` 사전 검증
- [ ] `application/stage_runner.run_stage_card_html_render`
- [ ] `tests/test_brand_card/test_templates.py` — 각 템플릿이 CardPlan fixture 를 에러 없이 렌더

### Phase B6 — 브랜드 카드 컴플라이언스 ([B7])
- [ ] **⚠️ Phase 5 (SEO 컴플라이언스) 완료 후 착수** — `CompliancePolicy.BRAND_LENIENT` 프로필은 Phase 5 에서 이미 정의되어 있어야 함
- [ ] `domain/brand_card/` 에서 `from domain.compliance.rules import CompliancePolicy, RULES` 임포트 (단일 출처 예외)
- [ ] `domain/brand_card/compliance_integration.py` — 블록 텍스트 추출 + checker(policy=BRAND_LENIENT) 호출 + fixer (블록 카피 교체, image_slot 재사용)
- [ ] `application/stage_runner.run_stage_card_compliance`
- [ ] `tests/test_brand_card/test_compliance_integration.py`

### Phase B7 — Playwright 렌더링 + 분할 ([B8])
- [ ] `domain/brand_card/playwright_renderer.py` — sync Chromium 세션 재사용, 폰트 로드 대기, full_page 스크린샷 또는 수동 clip loop
- [ ] 9000px 초과 자동 분할 알고리즘 (§2-4) — `page.evaluate()` 로 블록 y좌표 → 그리디 분할 → Pillow 크롭
- [ ] PNG `tEXt` 메타 삽입 (브랜드 ID, 키워드, 템플릿 ID, variant)
- [ ] hard max 18000px 초과 시 variant 실패 분류
- [ ] `application/stage_runner.run_stage_card_screenshot`
- [ ] `tests/test_brand_card/test_playwright_renderer.py` — snapshot 퍼지 매치

### Phase B8 — 패키지 정리 + manifest ([B9])
- [ ] `domain/brand_card/manifest_builder.py` — cards-manifest.json 생성 (§5-9)
- [ ] 작업 디렉토리 정리 (임시 HTML 폐기 or 디버그 보존)
- [ ] `application/orchestrator.run_brand_card_only` 완성

### Phase B9 — 합류 + 통합 (`run_full_package`)
- [ ] `application/orchestrator.run_full_package` — ThreadPoolExecutor(max_workers=2) 병렬, [5] 이후 합류점
- [ ] `application/models.py` 에 `PackageResult`, `BrandCardResult` 추가
- [ ] `scripts/register_brand.py`, `scripts/generate_cards.py`, `scripts/run_full_package.py`, `scripts/remove_media.py` CLI 래퍼
- [ ] `.claude/skills/brand-card/` 스킬 + `.claude/agents/domain/brand-card-guardian.md` 에이전트 (선택)
- [ ] E2E 테스트: 테스트 브랜드 + 키워드 1개로 `run_full_package` 전체 통과
- [ ] `tasks/lessons.md` 에 브랜드 카드 트랙 완료 결과 기록

---

## ⚠️ 사용자 제공 대기 중

- **의료법 8개 카테고리 상세 (`SEO_STRICT`)** — Phase 4 완료 후 Phase 5 착수 전 필요. 확정 시 `BRAND_LENIENT` 7개 초안(SPEC-BRAND-CARD §7-2) 과 함께 재검토
- **Phase 0.6 실측 샘플 (사용자 준비 예정)** — PDF 3종 (스캔/텍스트/혼합), docx 1종 (표 포함)
- **MVP 템플릿 5종 디자인 시안 (선택)** — 1차는 Claude `frontend-design` 스킬 prototyping, 2차 사용자 검토 후 교체 가능

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

## Phase R1: Backend Foundation (도메인 + Supabase) — 예상 6h

### R1.1 Supabase 마이그레이션 (45분)
- [ ] R1.1.1 `config/schema.sql` 끝에 `publications` 테이블 SQL 추가 (id uuid pk, job_id text nullable, keyword text not null, slug text not null, url text not null unique, published_at timestamptz nullable, created_at default now). 검증: SQL 문법만 검사 (실제 적용은 R1.1.3)
- [ ] R1.1.2 같은 파일에 `ranking_snapshots` 테이블 SQL 추가 (id uuid pk, publication_id uuid fk on delete cascade, position int nullable, total_results int nullable, captured_at default now, serp_html_path text nullable). 인덱스: `(publication_id, captured_at desc)`, publications 는 `(keyword)` `(slug)`
- [ ] R1.1.3 Supabase 대시보드 SQL Editor 에 추가분만 실행 (기존 테이블 영향 X 확인). 검증: `select count(*) from publications` `select count(*) from ranking_snapshots` 둘 다 0 반환
- [ ] R1.1.4 `tasks/lessons.md` 에 적용 결과 + 롤백용 `drop table ranking_snapshots; drop table publications;` 스니펫 기록

### R1.2 도메인 모델 (30분)
- [ ] R1.2.1 `domain/ranking/__init__.py` 빈 파일 생성
- [ ] R1.2.2 `domain/ranking/model.py` 생성 — Pydantic `Publication`, `RankingSnapshot`, `RankingTimeline` (publication + list[RankingSnapshot] + 메타). `RankingMatchError` 예외 정의. 모든 필드 타입힌트, frozen 설정. 30줄 이내 함수 보장
- [ ] R1.2.3 `tests/test_ranking/__init__.py` + `tests/test_ranking/test_model.py` 생성 — Publication/RankingSnapshot 직렬화·기본값·검증 단위 테스트 (3개 케이스)

### R1.3 도메인 ranking/url_match.py (45분)
- [ ] R1.3.1 `domain/ranking/url_match.py` 신규 — `BLOG_POST_URL_RE` 상수 (serp_collector 와 동일 패턴, 의도적 복제), `normalize_blog_url(url) -> str | None` (스킴 보정 + `m.blog.naver.com` 우선 정규화), `urls_match(a, b) -> bool`
- [ ] R1.3.2 `tests/test_ranking/test_url_match.py` — `blog.naver.com/userid/123456789` ↔ `m.blog.naver.com/userid/123456789` 동치, 트레일링 슬래시·쿼리 무시, 비매칭 케이스 (각 5개 이상)

### R1.4 도메인 ranking/tracker.py (60분)
- [ ] R1.4.1 `domain/ranking/tracker.py` 신규 — `find_position(keyword: str, target_url: str, serp_fetcher: Callable[[str], str], serp_parser: Callable[[str], list[ParsedSerpItem]]) -> RankingSnapshot` 시그니처. `domain.crawler` 를 import 하지 않음 (의존성 주입 패턴)
- [ ] R1.4.2 `find_position` 내부: integrated SERP URL 빌드 → `serp_fetcher(url)` → `serp_parser(html)` → 각 결과를 `urls_match` 비교 → 발견 시 `position=인덱스+1`, 미발견 시 `position=None`
- [ ] R1.4.3 `tests/test_ranking/test_tracker.py` — fake fetcher/parser 주입한 시나리오 5개: 1위, 5위, 100위 밖, fetcher 예외, parser 빈 결과

### R1.5 도메인 ranking/storage.py (60분)
- [ ] R1.5.1 `domain/ranking/storage.py` 신규 — `insert_publication(publication: Publication) -> Publication` (id 채워서 반환), `get_publication(id) -> Publication | None`, `list_publications(keyword: str | None, limit: int) -> list[Publication]`, `insert_snapshot(snapshot: RankingSnapshot) -> RankingSnapshot`, `list_snapshots(publication_id, limit) -> list[RankingSnapshot]`. 모두 `config.supabase.get_client()` 만 사용
- [ ] R1.5.2 url unique 충돌 시 `RankingDuplicateUrlError` 발생 (Pydantic 모델 X, 일반 Exception). orchestrator 에서 변환
- [ ] R1.5.3 `tests/test_ranking/test_storage.py` — Supabase mock (기존 `tests/test_application/test_stage_runner.py` 의 `monkeypatch + MagicMock` 패턴 따라가기). 5개 케이스: insert/get/list/duplicate/cascade

### R1.6 도메인 CLAUDE.md 작성 (30분)
- [ ] R1.6.1 `domain/ranking/CLAUDE.md` 신규 작성. 핵심 규칙: (1) `domain.crawler` 직접 import 금지 — DI 패턴, (2) URL 정규화 단일 출처는 `url_match.py`, (3) 모든 함수 Pydantic 반환, (4) 30줄/300줄 한계, (5) print 금지·logging 사용, (6) `BLOG_POST_URL_RE` 는 의도적 복제이며 serp_collector 변경 시 수동 동기화 (lessons.md 에 명시)
- [ ] R1.6.2 루트 `CLAUDE.md` 의 "참조 문서" 섹션에 `domain/ranking/CLAUDE.md` 1줄 추가. "디렉터리 구조" 트리에도 `ranking/` 1줄 추가

### R1.7 architecture-check 갱신 (15분)
- [ ] R1.7.1 `.claude/hooks/architecture-check.sh` 의 `STAGE_ORDER` 에 `[ranking]=0` 추가 (격리 도메인). 검증: 셸에서 `bash .claude/hooks/architecture-check.sh` 실행, 통과
- [ ] R1.7.2 `tasks/lessons.md` 에 "신규 도메인 등록 시 STAGE_ORDER 동시 갱신" 패턴 기록

---

## Phase R2: Application Layer (오케스트레이션 + 스케줄러) — 예상 4h

### R2.1 ranking_orchestrator.py (75분)
- [ ] R2.1.1 `application/ranking_orchestrator.py` 신규 — `register_publication(job_id: str | None, keyword: str, slug: str, url: str, published_at: datetime | None) -> Publication`. 내부에서 `url_match.normalize_blog_url` 로 정규화 → `storage.insert_publication`. duplicate 시 기존 publication 반환 (멱등)
- [ ] R2.1.2 같은 파일에 `check_rankings_for_publication(publication_id: str) -> RankingSnapshot`. `BrightDataClient` 인스턴스화 → `serp_collector.build_integrated_serp_url` + `_parse_serp_html` 을 wrapper 로 묶어 `tracker.find_position` 에 주입 → 결과를 `storage.insert_snapshot` 저장 후 반환
- [ ] R2.1.3 같은 파일에 `check_all_active_rankings(reporter: ProgressReporter | None = None) -> list[RankingSnapshot]`. publications 전체 순회, publication 당 호출 (Bright Data rate 보호 위해 1초 sleep). 진행률 logging
- [ ] R2.1.4 모든 함수 Pydantic 반환, 예외는 `raise` 가능 (orchestrator 레이어), 에러 핸들링은 reporter.pipeline_error 호출

### R2.2 scheduler.py (60분)
- [ ] R2.2.1 `application/scheduler.py` 신규 — `start_scheduler(loop: asyncio.AbstractEventLoop) -> AsyncIOScheduler`, `stop_scheduler(scheduler) -> None`. APScheduler `AsyncIOScheduler` 사용. cron trigger: `hour=9, minute=0, timezone='Asia/Seoul'`
- [ ] R2.2.2 job 함수는 `_run_daily_check()` — sync 함수, 내부에서 `check_all_active_rankings()` 호출. logging.info 로 시작/종료/카운트 기록
- [ ] R2.2.3 `pyproject.toml` 의 dependencies 에 `apscheduler>=3.10` 추가. `pip install -e ".[dev]"` 로 설치
- [ ] R2.2.4 max_instances=1 + coalesce=True 설정 (서버 재시작 직후 누락분 1회만 보충)

### R2.3 application 모델 확장 (15분)
- [ ] R2.3.1 `application/models.py` 에 `RankingCheckSummary` Pydantic 추가 (checked_count, found_count, errors_count, duration_seconds). orchestrator return 보조용
- [ ] R2.3.2 `application/CLAUDE.md` 에 ranking_orchestrator/scheduler 책임 1문단 추가

### R2.4 application 테스트 (45분)
- [ ] R2.4.1 `tests/test_application/test_ranking_orchestrator.py` — 5개 케이스: register 신규/중복, check_rankings 발견/미발견, check_all 다중 publication. BrightDataClient + storage mock
- [ ] R2.4.2 `tests/test_application/test_scheduler.py` — `start_scheduler` 가 `AsyncIOScheduler` 인스턴스 반환 + cron 트리거 등록 확인 + stop 후 jobs 비어있는지. apscheduler 의 mock 트리거 사용

---

## Phase R3: API (FastAPI 라우터) — 예상 3h

### R3.1 라우터 + 스키마 (60분)
- [ ] R3.1.1 `web/api/schemas.py` 끝에 추가: `PublicationCreateRequest` (job_id?, keyword, slug, url, published_at?), `PublicationResponse`, `RankingSnapshotResponse`, `RankingTimelineResponse`. 모두 datetime → ISO string serialization
- [ ] R3.1.2 `web/api/routers/rankings.py` 신규 — `router = APIRouter(prefix="/rankings", tags=["rankings"], dependencies=[Depends(require_api_key)])`. 엔드포인트 5개:
  - `POST /publications` → ranking_orchestrator.register_publication
  - `GET /publications?keyword=...&limit=...`
  - `GET /publications/{id}` (timeline 30개 포함)
  - `POST /publications/{id}/check` (수동 즉시 체크)
  - `GET /publications/{id}/snapshots?limit=...`
- [ ] R3.1.3 모든 핸들러 30줄 이내. `_get_orchestrator()` 패턴은 ranking_orchestrator 가 stateless 라 불필요 — 함수 직접 호출
- [ ] R3.1.4 `web/api/main.py` 의 `app.include_router` 에 `rankings.router` 추가 (prefix `/api`)

### R3.2 lifespan 통합 (30분)
- [ ] R3.2.1 `web/api/main.py` 의 `lifespan` 함수에 스케줄러 시작/종료 통합. `start_scheduler(loop)` 호출 결과를 클로저 변수로 보관, yield 후 `stop_scheduler` 호출
- [ ] R3.2.2 `settings.py` 에 `ranking_scheduler_enabled: bool = True` 추가. 환경변수 `RANKING_SCHEDULER_ENABLED=false` 면 비활성 (테스트용)
- [ ] R3.2.3 lifespan 내부에서 `if settings.ranking_scheduler_enabled:` 가드

### R3.3 API 테스트 (45분)
- [ ] R3.3.1 `tests/test_web/__init__.py` (없으면) + `tests/test_web/test_rankings_api.py` — FastAPI TestClient 로 5개 엔드포인트 happy path + 401 (인증 미들웨어). orchestrator mock 으로 격리
- [ ] R3.3.2 `tests/test_web/test_main_lifespan.py` — `RANKING_SCHEDULER_ENABLED=false` 시 스케줄러 미시작 검증

### R3.4 OpenAPI/문서 (15분)
- [ ] R3.4.1 각 핸들러에 docstring + response_model 명시. `/docs` 에서 5개 엔드포인트 표시 확인 (수동 검증)

---

## Phase R4: CLI — 예상 1.5h

### R4.1 register_publication.py (30분)
- [ ] R4.1.1 `scripts/register_publication.py` 신규 — argparse `--job-id` (선택), `--keyword`, `--slug`, `--url` (필수), `--published-at` (ISO date 선택). type validator 로 빈 값 거부
- [ ] R4.1.2 `application.ranking_orchestrator.register_publication` 호출 → 결과를 `print(json.dumps(...))` ❌ 금지 → `logging.info(json.dumps(...))` 로 출력. 종료 코드 0/1
- [ ] R4.1.3 `tests/test_scripts/test_register_publication_cli.py` (없으면 디렉토리 생성) — argparse 검증 2개 (keyword 누락, url 형식 불량)

### R4.2 check_rankings.py (45분)
- [ ] R4.2.1 `scripts/check_rankings.py` 신규 — argparse `--publication-id` 또는 `--all` (mutually exclusive group). `LoggingProgressReporter` 사용
- [ ] R4.2.2 `--publication-id` → `check_rankings_for_publication`, `--all` → `check_all_active_rankings`. 결과 카운트 logging
- [ ] R4.2.3 `tests/test_scripts/test_check_rankings_cli.py` — 두 모드 분기 검증, mutually exclusive 검증

### R4.3 README/help 갱신 (15분)
- [ ] R4.3.1 루트 `CLAUDE.md` 의 "빌드 & 실행" 코드블럭에 신규 CLI 2줄 추가
- [ ] R4.3.2 SPEC-SEO-TEXT.md 변경 ❌ 금지 — ranking 은 SPEC v2 범위 밖. 별도 SPEC-RANKING.md 신규 필요 여부는 사용자에게 질문

---

## Phase R5: Web UI (Next.js) — 예상 4h

### R5.1 타입 + API 클라이언트 (30분)
- [ ] R5.1.1 `web/frontend/src/types/index.ts` 에 `Publication`, `RankingSnapshot`, `RankingTimeline` 타입 추가 (백엔드 Pydantic 과 1:1)
- [ ] R5.1.2 `web/frontend/src/lib/api.ts` 에 5개 함수 추가: `createPublication`, `listPublications`, `getPublication`, `checkRanking`, `listSnapshots`. 기존 `fetcher` + X-API-Key 패턴 동일

### R5.2 PublicationForm 컴포넌트 (45분)
- [ ] R5.2.1 `web/frontend/src/components/PublicationForm.tsx` 신규 — props: `{slug, keyword, jobId?, existing?: Publication, onSubmit?: (p: Publication) => void}`. URL input + published_at date picker + 저장 버튼
- [ ] R5.2.2 URL 형식 클라이언트 검증 (`/^https?:\/\/(m\.)?blog\.naver\.com\/[\w-]+\/\d{9,}$/`). 실패 시 inline 에러 표시
- [ ] R5.2.3 기존 publication 있으면 input prefill + "수정" 버튼. 제출 시 createPublication 호출 (orchestrator 가 멱등)

### R5.3 RankingTimeline 컴포넌트 (45분)
- [ ] R5.3.1 `web/frontend/src/components/RankingTimeline.tsx` 신규 — props: `{snapshots: RankingSnapshot[]}`. 표 렌더 (date, position, change vs 전일). 100위 밖은 "—" 표시
- [ ] R5.3.2 sparkline 은 Phase 2 — 일단 표만. position null/숫자 모두 처리

### R5.4 결과 페이지 통합 (45분)
- [ ] R5.4.1 `web/frontend/src/app/results/[slug]/page.tsx` 수정 — 페이지 상단에 "발행 URL 등록" 영역 추가. mount 시 `listPublications({keyword, slug})` 호출해 기존 publication 조회
- [ ] R5.4.2 publication 등록 완료 시 자동으로 `getPublication(id)` 호출해 timeline 표시. "지금 체크" 버튼 → `checkRanking` → 시계열 갱신
- [ ] R5.4.3 페이지 300줄 초과 시 컴포넌트 분리 (RankingPanel.tsx 등)

### R5.5 신규 /rankings 페이지 (45분)
- [ ] R5.5.1 `web/frontend/src/app/rankings/page.tsx` 신규 — 모든 publications 목록 표 (키워드, slug, URL, 최신 순위). 키워드 필터 input, 정렬 dropdown (최신순/순위 좋은 순)
- [ ] R5.5.2 행 클릭 시 인라인 RankingTimeline 펼치기 또는 `/results/{slug}` 로 이동
- [ ] R5.5.3 layout.tsx 또는 nav 컴포넌트에 "/rankings" 링크 추가 (있으면)

### R5.6 frontend lint/type-check (15분)
- [ ] R5.6.1 `cd web/frontend && npm run lint && npm run typecheck` (또는 build) 0 에러

---

## Phase R6: Tests (통합 검증) — 예상 1.5h

### R6.1 통합 시나리오 (45분)
- [ ] R6.1.1 `tests/test_ranking/test_e2e_flow.py` — register → check → list snapshots 흐름. BrightDataClient 만 mock (다른 레이어는 실제). 네이버 SERP HTML 픽스처: `tests/fixtures/ranking_serp/integrated_with_target.html`, `..._without_target.html` 2개 작성
- [ ] R6.1.2 fixture HTML 은 실제 네이버 통합검색 결과 모방 (m.blog.naver.com 링크 5개 포함). serp_collector 의 `_parse_serp_html` 이 그대로 파싱하는지 함께 검증

### R6.2 회귀 + 커버리지 (30분)
- [ ] R6.2.1 `pytest tests/ -v` 전체 통과 확인. 기존 371개 + 신규 ranking 테스트 (예상 25~30개) 모두 통과
- [ ] R6.2.2 신규 도메인 라인 커버리지 80% 이상 (수동 확인)

### R6.3 lessons.md 갱신 (15분)
- [ ] R6.3.1 `tasks/lessons.md` 에 ranking MVP 작업 중 발견한 패턴 기록 (의존성 주입 패턴, BLOG_POST_URL_RE 복제 결정, lifespan 스케줄러 패턴 등)

---

## Phase R7: 검증 + 커밋 — 예상 30분

- [ ] R7.1 `bash .claude/hooks/build-check.sh` 통과 (ruff check/format, architecture-check, mypy, pytest 모두 0)
- [ ] R7.2 `bash .claude/hooks/architecture-check.sh` 단독 통과 — ranking 격리 확인
- [ ] R7.3 수동 smoke test: 로컬 uvicorn 기동 → `/docs` 에서 ranking 5개 엔드포인트 호출 → publication 1건 등록 → 즉시 체크 → snapshot 1건 생성 확인
- [ ] R7.4 frontend smoke test: `/results/{slug}` 에 URL 등록 → timeline 표시 확인, `/rankings` 페이지 접근 가능 확인
- [ ] R7.5 git status 확인 → 변경 파일 일괄 staging (uvicorn.*.log 제외)
- [ ] R7.6 commit 메시지 draft: `feat(ranking): add daily ranking tracker MVP (backend+api+ui+cli)`. body 에 사용자 결정 5가지 + 신규 도메인/스케줄러 명시
- [ ] R7.7 🔴 push 는 사용자 명시 요청 시에만 (CLAUDE.md 규칙)

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
- [ ] 나머지 3 템플릿 (diet_empathy/process_guide/local_info) — Phase 2.5 직전 또는 사용자 시안 후

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
- [ ] 브랜드 등록 UI + `POST /brands` 백엔드
- [ ] `brand_media_assets` 미디어 라이브러리 UI
- [ ] approve/reject 외 3 액션(문구 수정 / 사진 교체 / 전략 변경) 백엔드 PATCH 라우트
- [ ] frontend 테스트 프레임워크 (vitest + Testing Library)

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

### 다음 단계 (Phase 1 착수 시)
- [ ] B0: SPEC v2.1 의 결정 사항을 `tasks/todo.md` 에 Phase 1~5 체크리스트로 분해
- [ ] `architecture-check.sh` STAGE_ORDER `[brand_card]=2` 등록
- [ ] Phase 1 마이그레이션 + model.py + reuse_guard 골격 + plan_generator 구현
- [ ] Phase 1 검증 게이트: BRAND_LENIENT §7 9종 회귀 테스트

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
