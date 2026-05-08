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

<!-- archived to tasks/_archive/todo-2026-q2.md (Phase 1 + Phase 2 실측 + Phase 2~8 SEO 트랙) -->

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

### J1.2 운영 env 동시성 하향 (Render Dashboard, 코드 변경 0)
- [ ] **사용자 작업** — `IMAGE_PARALLEL_WORKERS=2` (기본 5 → Gemini 병렬 base64 메모리 절감)
- [ ] **사용자 작업** — `BRIGHTDATA_CONCURRENT_LIMIT=3` (기본 5)
- [ ] **사용자 작업** — `BATCH_MAX_WORKERS=1` (기본 2)
- [x] `config/.env.example` 주석에 운영 권장값 기록 — Phase J1.2 헤더 + 3개 키 권장값 코멘트 추가

### J1.3 Render Service Instance 업그레이드
- [ ] **사용자 작업** — `render.yaml:7` `plan: starter` → `plan: standard` (RAM 512MB→2GB, CPU 0.5→1.0, +$18/mo)
- [ ] **사용자 작업** — 업그레이드 후 24시간 메모리 그래프 모니터링 (피크 사용량 < 1.5GB 확인)
- [ ] commit msg 에 비용 차이 명시 — render.yaml 변경 commit 시점에 사용자가 기록

### J1.4 재시작 알림 (notifier 재사용) ✅ (2026-05-08)
- [x] `web/api/main.py` startup hook 에 "재시작 감지" 로직 — `RENDER_INSTANCE_ID` 또는 hostname 식별 → `notifier.send_text(":arrows_clockwise: *백엔드 재시작 감지* — instance=...")` 1회 발송. logger.info 도 동시 기록
- [x] Slack webhook 미설정 시 noop (기존 패턴 유지) — `notifier.send_text` 자체가 webhook 부재 시 즉시 return

### J1.5 검증 + commit
- [x] `bash .claude/hooks/build-check.sh` 그린 — pyright 시스템 미설치 SKIP, ruff/format 그린, useJobPolling vitest 5/5. 풀 vitest 136 passed + PublicationActionRow/PublicationForm 2 file failed 는 baseline `swr` import 사전 실패 (내 변경과 무관, stash 후 동일 재현 확인)
- [x] commit `feat(ops): Phase J1 — 폴링 retry-bound + 재시작 알림 + .env.example 권장값` — render.yaml 미변경 (사용자 인계)
- [ ] **사용자 작업** — 운영 1주 모니터링 (메모리 그래프 + 502/404 발생 빈도) → Phase J2 착수 결정

---

## 💾 Phase J2 — Job 상태 Supabase 영속화 (Phase J1 완료 후, 2~3주)

> in-memory dict 를 정본에서 제거하고 **Supabase 가 단일 출처**, in-memory 는 캐시로 강등. 컨테이너 재시작 후에도 `GET /api/jobs/{id}` 가 200 OK + `status=orphaned` 같은 의미있는 종결을 반환. SPEC-BATCH 의 `domain/batch/storage.py` 와 동일한 single-source-of-truth 정신. **`application/orchestrator.run_pipeline` 시그니처 무변경** (단일 흐름 보호).

### J2.1 schema — jobs 테이블
- [ ] `config/schema.sql` 에 `jobs` 테이블 추가:
  - `id text PRIMARY KEY` (12-hex uuid prefix)
  - `type text` (pipeline|analyze|generate|validate|brand_card_render|ranking_bulk_check)
  - `status text` (pending|running|succeeded|failed|cancelled|timed_out|**orphaned**)
  - `params jsonb`, `result jsonb`, `error text`
  - `created_at timestamptz`, `started_at`, `finished_at`, `last_heartbeat`
  - `instance_id text` (Render hostname — 누가 잡고 있는지)
- [ ] index: `(status, last_heartbeat)` — orphaned sweep 용
- [ ] `progress_events` 별도 테이블 신설 — `(job_id text, seq int, event jsonb, created_at)`. jobs.progress_log jsonb 누적 폭주 회피

### J2.2 storage layer 신규
- [ ] `web/api/job_store.py` — Supabase CRUD (`insert_job`/`get_job`/`update_job_status`/`update_heartbeat`/`append_progress_event`/`list_orphaned_jobs`)
- [ ] `domain/batch/storage.py` 코드 스타일 그대로 복제 (격리 도메인 정신)

### J2.3 JobManager write-through 전환
- [ ] `_submit` — in-memory dict 에 넣기 직전 `job_store.insert_job` (transactional)
- [ ] `_run_job` — status 전환 (`running`/`succeeded`/`failed`/`timed_out`/`cancelled`) 마다 `update_job_status`
- [ ] 30초 daemon thread 로 `update_heartbeat` 갱신
- [ ] `event_bus.emit` → `append_progress_event` (별도 테이블, fire-and-forget)

### J2.4 GET /api/jobs/{id} DB fallback
- [ ] `web/api/routers/jobs.py` — in-memory `get_job` 결과가 None 이면 `job_store.get_job` 조회 후 200 OK
- [ ] 클라이언트는 `status=orphaned` 도 정상 종결로 인식 (Phase J1 의 retry-bound 와 별개로 자연 종결)

### J2.5 startup + 주기 sweep
- [ ] `web/api/main.py` startup — 자기 instance_id 의 `status=running` job 을 모두 `orphaned` 마킹 (자기 컨테이너가 죽었다 살아난 것)
- [ ] 5분 주기 sweep — `status=running AND last_heartbeat < now() - 5min` → `orphaned` (다른 인스턴스가 죽은 경우)
- [ ] sweep 결과 알림 (notifier) — orphaned > 0 시 1회 발송

### J2.6 결과 경로 영속화
- [ ] `jobs.result` 에 `output/{slug}/{ts}/` 경로 + Supabase Storage URL 모두 기록
- [ ] 재시작 후 클라이언트가 결과 다운로드 가능 (현재 휘발성 컨테이너 fs 의존성 제거)

### J2.7 테스트
- [ ] `tests/test_web/test_job_store.py` — CRUD + orphaned sweep 쿼리
- [ ] `tests/test_web/test_job_manager_persistence.py` — submit → DB insert 검증, in-memory miss → DB fallback, status 전환마다 update 호출
- [ ] `tests/test_web/test_orphaned_sweep.py` — last_heartbeat 만료 시 자동 orphaned 마킹

### J2.8 검증 + commit + 운영 검증
- [ ] `bash .claude/hooks/build-check.sh` 그린
- [ ] commit `feat(ops): Phase J2 — Job 상태 Supabase 영속화 + orphaned 자동 종결`
- [ ] **staging 강제 재시작 테스트**: Render Dashboard 에서 일부러 Manual Deploy → 진행 중 job 이 `orphaned` 로 자연 종결되는지 검증

---

## ⚠️ Phase J 위험 요소

- **DB write 가 응답 latency 추가**: `submit_*` 이 DB insert 후 응답. Supabase ~100ms 추가. 모니터링 필요. 임계 시 fire-and-forget + retry 전환
- **progress_events 테이블 폭주**: 단계별 이벤트가 분당 수십 건. 7일 retention cron + 인덱스 `(job_id, seq)`. Phase J2.1 의 별도 테이블 분리는 이를 위함
- **false orphaned**: heartbeat grace 5분. 더 짧으면 정상 job 도 orphaned 처리 위험. 운영 데이터 누적 후 조정
- **단일 흐름 보호**: `application/orchestrator.run_pipeline` / `run_analyze_only` / `run_generate_only` 시그니처 절대 무변경. 변경 영역은 `web/api/job_manager.py` + 신규 `web/api/job_store.py` + 신규 schema 만
- **rollout**: J2 는 큰 변경이라 feature flag (`JOB_PERSISTENCE_ENABLED`) 로 단계 도입 — env=false 시 기존 in-memory 동작 그대로

## 🔮 Phase J 후속 (별도 todo 진입 시 분해)

- **Phase J3 — Worker 분리**: API stateless + Render Background Worker. Postgres `FOR UPDATE SKIP LOCKED` 큐 (SPEC-BATCH `claim_item_for_dispatch` 패턴 재사용)
- **Phase J4 — Playwright 격리**: 브랜드 카드 렌더만 별도 서비스 (Vercel Sandbox 또는 Browserless). API/Worker 메모리 200~300MB 절감
- **Phase J5 — Durable workflow**: Inngest 또는 Temporal. 의료법 fixer/이미지 재시도/약한 섹션 보강을 step 단위 체크포인트화. 도입 시점은 J2~J4 안정화 + 운영 데이터 누적 후 trade-off 평가


