# Contents Creator — Todo

> 현재: Phase 0 부트스트랩 완료 → Phase 0.5 실측 3개 + 환경 변수 완결 대기

## ✅ 완료

- [x] v1 프로젝트 초기화 — 2026-04-15
- [x] SPEC-SEO-TEXT.md v2 작성 — 2026-04-15
- [x] 블로그 해시태그 분석 반영 — 2026-04-15
- [x] 2차 비평 반영 (C1 iframe 실측, M1 fixer, M2 차별화 N<10, M3 schema_version, M4 태그 클램프 제거, M5 outline.md) — 2026-04-15
- [x] Harness 구성 (5 skills + 5 agents + 2 hooks + settings.json) — 2026-04-15
- [x] CLAUDE.md (루트 + 5 도메인) — 2026-04-15
- [x] Phase 2 Next.js 대비 application 레이어 설계 — 2026-04-15
- [x] 프로젝트 스캐폴딩 (pyproject, .gitignore, config, application, scripts, 도메인 패키지) — 2026-04-15

## 🧪 Phase 0.5 — 1단계 착수 전 실측 (블로킹)

### [Pre-1] 개발 환경 준비
- [ ] `python -m venv .venv` 후 활성화
- [ ] `pip install -e ".[dev]"` 실행 성공 확인
- [ ] `bash .claude/hooks/build-check.sh` 그린 확인 (스켈레톤 기준)
- [ ] Supabase 프로젝트 생성 + `config/schema.sql` 적용

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

### [Pre-2] 환경 변수 전체 완결
- [ ] `config/.env` 에 다음 키 모두 채움:
  - `BRIGHT_DATA_API_KEY`, `BRIGHT_DATA_WEB_UNLOCKER_ZONE` (SERP 도 Web Unlocker 로 처리)
  - `ANTHROPIC_API_KEY`
  - **`GEMINI_API_KEY`** (Google AI Studio 발급 — Gemini 3.1 Flash Image Preview 용)
  - `SUPABASE_URL`, `SUPABASE_KEY`
- [ ] `python -c "from config.settings import settings; print(settings.bright_data_api_key is not None)"` 로 로드 확인

## 🚧 Phase 1 — 크롤러 도메인 (SPEC-SEO-TEXT.md §3 [1][2])

- [ ] `domain/crawler/model.py` — `SerpResult`, `BlogPage`, `InsufficientCollectionError`
- [ ] `domain/crawler/brightdata_client.py` — 공통 HTTP, 재시도, 타임아웃
- [ ] `domain/crawler/serp_collector.py` — 네이버 블로그 URL 필터, 최소 7개
- [ ] `domain/crawler/page_scraper.py` — Web Unlocker 호출 (C1 결과 반영)
- [ ] `application/stage_runner.py` 에 `run_stage_serp_collection`, `run_stage_page_scraping` 추가
- [ ] `tests/test_crawler/` 단위 테스트 (mock 기반)
- [ ] 실제 키워드 1개로 end-to-end 수집 검증
- [ ] `bash .claude/hooks/build-check.sh` 통과
- [ ] `tasks/lessons.md` 에 수집 결과 기록

## 🔮 Phase 2~7 — 이후 단계 (각 단계 착수 시 분해)

- Phase 2: 물리 분석 (`physical_extractor`) — 이미지 메타 추출 포함 (`image_pattern`)
- Phase 3: 의미 + 소구 + 교차 분석 (`semantic_extractor`, `appeal_extractor`, `cross_analyzer`, `pattern_card`)
- Phase 4: 생성 (`prompt_builder`, `outline_writer`, `body_writer`) — M2 불변 규칙 + image_prompts 생성
- Phase 5: 의료법 검증 (`rules`, `checker`, `fixer`) — 본문/태그/이미지 prompt 동시 검증. 사용자 제공 8개 카테고리 필요
- **Phase 6: AI 이미지 생성** 🆕 (`domain/image_generation/`) — Gemini 3.1 Flash Image Preview, 캐시 + 예산 + 재시도
- Phase 7: 조립 (`assembler`, `outline_md`, `naver_html`) — outline.md 에 이미지 매핑 가이드
- Phase 8: 통합 + E2E 테스트 + `run_pipeline` 본문 채움

## ⚠️ 사용자 제공 대기 중

- **의료법 8개 카테고리 상세** — Phase 4 완료 후 Phase 5 착수 전 필요
- **Bright Data 계정·zone** — Phase 0.5 실측 블로커

## 📌 상시 확인

- [ ] 코드 변경 시 `bash .claude/hooks/build-check.sh` 통과
- [ ] 의료 콘텐츠 관련 변경 시 `python scripts/validate.py` 추가 실행
- [ ] 사용자 교정 받으면 즉시 `tasks/lessons.md` 에 기록
