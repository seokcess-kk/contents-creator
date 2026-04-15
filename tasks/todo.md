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
