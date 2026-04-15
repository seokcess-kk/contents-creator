<!--
이 파일은 점진적으로 개선됩니다.
Claude가 실수하거나 의도와 다른 결과를 낼 때마다,
해당 케이스를 방지하는 규칙을 한 줄씩 추가하세요.
-->

# Contents Creator — 네이버 SEO 원고 생성 엔진

## 개요

네이버 키워드 → Bright Data 크롤링 → 상위글 분석 → 패턴 카드 → SEO 원고 → 의료법 검증 → AI 이미지 생성(Gemini) → 네이버 호환 출력의 10단계 내부 파이프라인 도구.

- **포지셔닝**: "AI 글쓰기 도구"가 아닌 "레퍼런스 분석 기반 콘텐츠 생성"
- **기술 스택**: Python 3.11+, Bright Data (SERP + Web Unlocker), Supabase (PostgreSQL), Anthropic Claude SDK (Opus 4.6 / Sonnet 4.6), BeautifulSoup, Pydantic, ruff, mypy, pytest
- **아키텍처**: SDD (Spec Driven) + DDD (Domain Driven)
- **상세 설계**: @SPEC-SEO-TEXT.md

## 빌드 & 실행

```bash
# 환경 설정 (최초 1회)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 파이프라인 실행
python scripts/run_pipeline.py --keyword "<키워드>"   # 전체 [1]~[9]
python scripts/analyze.py --keyword "<키워드>"        # [1]~[5]만
python scripts/generate.py --keyword "<키워드>"       # [6]~[9]만 (DB 최신 패턴 카드)
python scripts/validate.py --content <경로>           # [8]만

# 검증
pytest                                      # 테스트
ruff check .                                # 린트
ruff format --check .                       # 포맷 체크
mypy domain/ application/                   # 타입 체크 (두 레이어 모두)
bash .claude/hooks/build-check.sh           # 위 4개 일괄 실행
```

## 디렉터리 구조

```
domain/              ← 순수 도메인 레이어 (I/O·표현 없음, Pydantic 반환)
├── crawler/         ← [1][2] Bright Data 기반 네이버 블로그 수집
├── analysis/        ← [3][4a][4b][5] 물리·의미·소구·교차 분석
├── generation/      ← [6][7] 아웃라인·도입부·본문 (M2 불변)
├── compliance/      ← [8] 의료법 3중 방어
└── composer/        ← [9] 조립 + 네이버 HTML + outline.md 변환
application/         ← Application Service 레이어 (도메인 오케스트레이션)
├── orchestrator.py  ← run_pipeline / run_analyze_only / run_generate_only / run_validate_only
├── stage_runner.py  ← 단계별 실행 헬퍼 (에러 핸들링, 진행 리포트)
├── progress.py      ← ProgressReporter 프로토콜 + 기본 구현
└── models.py        ← PipelineResult, StageStatus 등
scripts/             ← 얇은 CLI 래퍼 (argparse → application 호출)
tests/               ← application/ + domain/ 테스트
config/              ← .env, settings.py, supabase.py, schema.sql
.claude/             ← 하네스 (skills, agents, hooks, settings.json)
dev/active/          ← 외부 기억 장치 (plan, context)
tasks/               ← todo.md, lessons.md
output/{slug}/{YYYYMMDD-HHmm}/  ← 타임스탬프 서브디렉토리 (재실행 이력 누적)
```

**레이어 import 규칙:**
- `application/` → `domain/` 자유롭게 import 가능
- `domain/` → `application/` **금지** (역방향)
- `domain/` ↔ `domain/` **금지** (도메인 간 격리)
- `scripts/` → `application/` 만 (domain 직접 호출 금지)
- Phase 2 FastAPI 도 `application.orchestrator.*` 를 호출 (SPEC-SEO-TEXT.md §12 참조)

## 도메인 용어

- **패턴 카드(`PatternCard`)**: 키워드별 상위글 분석 집계. `schema_version: "2.0"` 필수. 분석 1번, 생성 N번의 자산. Supabase `pattern_cards` 테이블 + 파일 이중 저장
- **[3] 물리 추출**: DOM 파싱 (글자수, DIA+ 요소, 키워드 밀도, 블로그 태그). LLM 불필요
- **[4a] 의미 추출**: LLM 기반 섹션 역할·독자·제목·훅 (Sonnet 4.6)
- **[4b] 소구 포인트 추출**: LLM 기반 소구 포인트·홍보성 레벨 (Sonnet 4.6). **[4a]와 분리 필수**
- **[5] 교차 분석**: 비율 80/50/30 임계값 집계. **N<10일 때 차별화 섹션 생략**
- **도입부(intro)**: [6]에서 확정하는 200~300자 톤 락. [7] 본문에서 **재생성 금지**
- **DIA+ 요소**: `tables`, `lists`, `blockquotes`, `bold_count`, `separators`, `qa_sections`, `statistics_data` 7종
- **블로그 태그**: 네이버 포스트 하단 해시태그. `suggested_tags`는 본문 미삽입, `outline.md` 메타에만
- **의료법 3중 방어**: 1차 사전 주입 → 2차 사후 검증 → 3차 자동 수정 (최대 2회)
- **fixer 동작**: 구절 치환 기본, 실패 시 해당 문단 재생성 (도입부 제외)
- **`Client Profile`**: 확장 단계 개념. 현재 MVP 범위 밖. `User`(이 도구 사용자)와 구분

## 코딩 규칙

### 구조
- **레이어 격리**: `domain/` ↔ `domain/` 직접 import 금지. 도메인 조합은 `application/` 에서만
- `domain/` 은 `application/` 을 import 할 수 없다 (역방향 금지)
- `scripts/` 는 `application/` 만 호출. `domain/` 직접 호출 금지
- 각 도메인은 `model.py` (Pydantic) + 서비스 파일 + 필요 시 `repository.py`
- `domain/` 함수는 반드시 Pydantic 모델 반환. stdout 출력·파일 경로 문자열 반환 금지 (UI 비종속 원칙)
- 함수 30줄 이내. 파일 300줄 이내. 초과 시 분리

### 네이밍
- 파일/변수: `snake_case`, 클래스: `PascalCase`, 상수: `UPPER_SNAKE_CASE`
- SPEC 용어는 영문명 그대로 (`PatternCard`, `AppealPoint`, `DiaPlus`, `ComplianceReport`)

### 필수 패턴
- 모든 함수 시그니처에 타입 힌트
- 도메인 모델은 Pydantic `BaseModel`
- 외부 API 호출은 재시도 + 명시적 타임아웃 (Bright Data, Anthropic, Supabase)
- **LLM 호출은 Anthropic SDK `tool_use` 로 JSON 스키마 강제** (텍스트 "JSON으로 답해" 금지)
- 환경 변수는 `config/settings.py` 에서만 로드 (`os.environ` 직접 접근 금지)
- 임계값·매직 넘버는 상수 모듈로 승격

### 금지 패턴
- `print()` 디버깅 금지 (`logging` 사용)
- `from x import *` 금지
- bare `except:` 금지 (구체적 예외)
- 의료법 금지 표현 하드코딩 금지 (`domain/compliance/rules.py` 단일 출처)
- `--no-verify`, 테스트 skip 처리로 에러 우회 금지

### 🔴 M2 불변 규칙 (절대 위반 불가)
- `domain/generation/body_writer.py` 의 `generate_body()` 는 intro 원문 파라미터를 가질 수 없다
- 허용: `intro_tone_hint: str` (힌트만)
- 프롬프트 문자열에도 도입부 원문 삽입 금지
- 최종 조립은 `composer/assembler.py` 가 프로그래매틱 concat
- `post-edit-lint.sh` 훅 + `seo-writer-guardian` 에이전트 자동 차단

## 검증 규칙 (Self-Verification)

### 코드 변경 후 필수 순서
1. `ruff check .` — 린트 0개
2. `ruff format --check .` — 포맷 0개
3. `mypy domain/` — 타입 에러 0개
4. `pytest` — 관련 테스트 통과
5. 의료 콘텐츠 변경 시 → `python scripts/validate.py` 추가 실행
6. 일괄 실행: `bash .claude/hooks/build-check.sh`

### 에러 대응
- 에러 발생 시 사용자에게 보고만 말 것. 원인 분석 → 수정 → 재검증까지 자체 완료
- 3회 시도 후에도 해결 불가 시에만 사용자에게 판단 요청
- `auto-error-resolver` 에이전트 활용 가능

### 완료 판정
- "스태프 엔지니어가 승인할 수준인가?" 자문 후 제출
- YAGNI: 미래를 위한 빈 껍데기·불필요한 추상화·쓰지 않을 플래그 금지
- 단순한 수정은 과잉 설계 금지

## 의료광고법 — 타협 없음

- 의료 콘텐츠 생성/수정 시 반드시 compliance 도메인 경유
- 8개 위반 카테고리는 `domain/compliance/rules.py` **단일 출처**
- 3중 방어: 사전 주입 → 사후 검증 → 자동 수정 (최대 2회)
- fixer는 구절 치환 우선, 폴백으로 해당 문단 재생성 (도입부 제외)
- 이미지 내 텍스트도 검증 대상 (확장 단계)
- 상세: @.claude/skills/medical-compliance/SKILL.md

## 워크플로우

- 3단계 이상 작업 또는 아키텍처 결정 → 반드시 plan mode 진입
- 계획은 `tasks/todo.md` 체크리스트로 작성 → 사용자 확인 후 구현 시작
- 진행 중 문제 발생 시 즉시 멈추고 재계획. 밀어붙이지 않음
- 리서치·병렬 분석은 서브에이전트에 위임 (1 에이전트 = 1 작업)
- 완료 항목은 즉시 체크 표시

## 자기 개선

- 사용자 교정 받으면 즉시 `tasks/lessons.md` 에 패턴 기록
- 세션 시작 시 `tasks/lessons.md` 리뷰
- 반복 실수 패턴 발견 시 이 `CLAUDE.md` 에 규칙 한 줄 추가

## 참조 문서

- @SPEC-SEO-TEXT.md — 전체 기획서 (10단계 파이프라인, 스키마, 모델 매핑, 검증 기준)
- @SPEC-BRAND-CARD.md — 브랜드 카드 트랙 기획서 (병행 트랙, BRAND_LENIENT 프로필). SEO 트랙과 코드 격리
- @.claude/skills/content-pipeline/SKILL.md — 파이프라인 오케스트레이터
- @.claude/skills/crawling/SKILL.md — [1][2] Bright Data 규칙
- @.claude/skills/analysis/SKILL.md — [3][4a][4b][5] 분석 규칙
- @.claude/skills/generation/SKILL.md — [6][7] 생성 규칙 (M2 불변)
- @.claude/skills/medical-compliance/SKILL.md — [8] 의료법 3중 방어
- @application/CLAUDE.md — Application 레이어 오케스트레이션 규칙
- @SPEC-SEO-TEXT.md §12 — Phase 2 Web UI 대비 (Next.js + FastAPI 확장 지점)
- @tasks/todo.md — 현재 작업 체크리스트
- @tasks/lessons.md — 실수 패턴 기록
- @dev/active/ — plan, context 외부 기억 장치

## 변경 이력

- `2026-04-15`: 초판 작성. SPEC v2 기반 프로젝트 부트스트랩. M2 불변 규칙, [4a]/[4b] 분리, 비율 임계값, fixer 동작 방식, 블로그 태그 분석 반영
- `2026-04-15`: `application/` 레이어 추가 (Phase 2 Next.js + FastAPI 대비). 레이어 import 규칙·UI 비종속 원칙 명시

<!--
점진 개선 안내: Claude의 실수 패턴을 발견할 때마다 이 파일에 규칙을 한 줄씩 추가하세요.
예: "Bright Data SERP 응답의 광고 섹션은 반드시 제외할 것 (2026-05-XX 잘못 포함된 사례 있음)"
-->
