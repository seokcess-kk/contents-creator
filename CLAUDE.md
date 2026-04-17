<!--
이 파일은 점진적으로 개선됩니다.
Claude가 실수하거나 의도와 다른 결과를 낼 때마다,
해당 케이스를 방지하는 규칙을 한 줄씩 추가하세요.
-->

# Contents Creator — 네이버 SEO 원고 생성 엔진

네이버 키워드 → Bright Data 크롤링 → 상위글 분석 → 패턴 카드 → SEO 원고 → 의료법 검증 → AI 이미지 생성(Gemini) → 네이버 호환 출력의 10단계 파이프라인.
기술 스택: Python 3.11+, Bright Data, Supabase, Anthropic Claude SDK, Google Gemini, BeautifulSoup, Pydantic.
상세 설계: SPEC-SEO-TEXT.md

## 빌드 & 실행

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/run_pipeline.py --keyword "<키워드>"   # 전체 [1]~[10]
python scripts/analyze.py --keyword "<키워드>"        # [1]~[5]
python scripts/generate.py --keyword "<키워드>"       # [6]~[10] (DB 최신 패턴 카드)
python scripts/validate.py --content <경로>           # [8] 의료법 검증만
bash .claude/hooks/build-check.sh                     # 린트+포맷+타입+테스트 일괄
```

## 디렉터리 구조

```
domain/              ← 순수 도메인 (I/O 없음, Pydantic 반환)
├── crawler/         ← [1][2] Bright Data 크롤링
├── analysis/        ← [3][4a][4b][5] 물리·의미·소구·교차 분석
├── generation/      ← [6][7] 아웃라인·도입부·본문
├── compliance/      ← [8] 의료법 3중 방어
├── image_generation/← [9] Gemini 이미지 생성
└── composer/        ← [10] 조립 + 네이버 HTML
application/         ← 오케스트레이션 (도메인 조합, 진행 리포트)
scripts/             ← 얇은 CLI 래퍼 (argparse → application)
config/              ← .env, settings.py, supabase.py
output/{slug}/{ts}/  ← 타임스탬프별 결과물 (재실행 이력 누적)
```

## 레이어 import 규칙

- `scripts/` → `application/` → `domain/` (단방향만 허용)
- `domain/` → `application/` **금지** (역방향)
- `domain/` ↔ `domain/` **금지** (도메인 간 격리)
- `domain/` 함수는 Pydantic 모델 반환. stdout 출력·파일 경로 반환 금지

## 도메인 용어

- **패턴 카드(`PatternCard`)**: 키워드별 상위글 분석 집계. `schema_version: "2.0"`. 분석 1번, 생성 N번
- **DIA+ 요소**: tables, lists, blockquotes, bold_count, separators, qa_sections, statistics_data 7종
- **도입부(intro)**: [6]에서 확정하는 200~300자 톤 락. [7] 본문에서 재생성 금지
- **의료법 3중 방어**: 1차 사전 주입 → 2차 사후 검증 → 3차 자동 수정 (최대 2회)

## 코딩 규칙

- 파일/변수: `snake_case`, 클래스: `PascalCase`, 상수: `UPPER_SNAKE_CASE`
- 함수 30줄 이내. 파일 300줄 이내
- 모든 함수 시그니처에 타입 힌트. 도메인 모델은 Pydantic `BaseModel`
- LLM 호출은 Anthropic SDK `tool_use`로 JSON 스키마 강제 (텍스트 "JSON 답해" 금지)
- 외부 API 호출에 재시도 + 타임아웃 필수 (Bright Data, Anthropic, Supabase, Gemini)
- 환경 변수는 `config/settings.py`에서만 로드 (`os.environ` 직접 접근 금지)
- 임계값·매직 넘버는 상수 모듈로 승격
- **금지**: `print()`, `from x import *`, bare `except:`, `--no-verify`, 의료법 금지 표현 하드코딩

## 🔴 3계층 품질 강제 시스템

| 계층 | 시점 | 파일 | 통제 방식 |
|---|---|---|---|
| Layer 1 | [6] 아웃라인 후 | `outline_validator.py` | 섹션 수·이미지 수·도입부 길이 코드 검증 → 미달 시 1회 재생성 |
| Layer 2 | [7] 본문 후 | `body_quality_enforcer.py` | 섹션별 글자수·키워드 검증 → 약한 섹션만 Sonnet으로 보강 |
| Layer 3 | [10] 조립 시 | `assembler.py` | 이미지 위치를 LLM position 무시, `_build_even_image_map()`으로 균등 배분 |

## 🔴 분석→생성 반영 규칙 (Analysis-to-Generation Integrity)

프롬프트만으로는 LLM 출력을 통제할 수 없다. 코드 검증 + 부분 재생성으로 강제한다.

- 분석값 0 또는 빈 배열 → 그대로 전달 금지, 폴백 로직 필수 (태그 0개→키워드 기반 8개)
- 프롬프트 내 지시 모순 금지 (예: "소제목 1개" vs "필수 섹션 3개" 동시 지시)
- 키워드 밀도 반올림: `round(x, 4)`
- 소제목 수: 분석 avg < 2이면 필수+빈출 섹션 수 기반 보정 (SEO 최소 4개)
- 톤앤매너: 친근한 전문가 톤 (1인칭 `저는/제가` 금지, 구어체 혼합)
- 이미지 삽입 무결성: outline 수 = 생성 수 = MD 수 = HTML `<img>` 수
- `quality-report.json`: 글자수 ±20%, 키워드 밀도, 이미지 일치 자동 체크
- 물리 분석 regression 테스트: `tests/fixtures/naver_html/` 실측 HTML 12개

## 🔴 M2 불변 규칙 (절대 위반 불가)

- `body_writer.py`의 `generate_body()`는 intro 원문 파라미터를 가질 수 없다 (허용: `intro_tone_hint: str`)
- 프롬프트 문자열에도 도입부 원문 삽입 금지
- 최종 조립은 `composer/assembler.py`가 프로그래매틱 concat
- `post-edit-lint.sh` 훅 + `seo-writer-guardian` 에이전트 자동 차단

## 의료광고법 — 타협 없음

- 의료 콘텐츠 생성/수정 시 반드시 compliance 도메인 경유
- 8개 위반 카테고리는 `domain/compliance/rules.py` **단일 출처**
- checker에 SEO 키워드 컨텍스트 전달 — 키워드 자체를 오탐하지 않도록
- fixer에 금지 표현 목록 주입 — 수정 시 새 위반 생성 방지
- 톤 지시와 의료법 규칙 충돌 주의: "경험 공유"→1인칭 유도 위험 → "친근한 전문가 톤" 사용
- 상세: @domain/compliance/CLAUDE.md

## 검증 규칙

```bash
ruff check .                    # 린트 0개
ruff format --check .           # 포맷 0개
mypy domain/ application/       # 타입 에러 0개
pytest                          # 테스트 통과
bash .claude/hooks/build-check.sh  # 위 4개 일괄
```

- 에러 발생 시 원인 분석 → 수정 → 재검증까지 자체 완료. 3회 실패 후에만 사용자에게 판단 요청
- YAGNI: 불필요한 추상화·미래용 빈 껍데기 금지

## 워크플로우

- 3단계 이상 작업 → plan mode 진입, `tasks/todo.md` 체크리스트 → 사용자 확인 후 구현
- 리서치·병렬 분석은 서브에이전트 위임 (1 에이전트 = 1 작업)
- 사용자 교정 → 즉시 `tasks/lessons.md`에 패턴 기록

## 참조 문서

- SPEC-SEO-TEXT.md — 전체 기획서 (10단계 파이프라인, 스키마, 모델 매핑)
- SPEC-BRAND-CARD.md — 브랜드 카드 트랙 (병행, BRAND_LENIENT 프로필)
- application/CLAUDE.md — Application 레이어 오케스트레이션 규칙
- domain/analysis/CLAUDE.md — [3][4a][4b][5] 분석 규칙 + DIA+ + 물리 파싱
- domain/generation/CLAUDE.md — [6][7] 생성 규칙 + M2 불변 + 이미지 prompt
- domain/compliance/CLAUDE.md — [8] 의료법 3중 방어 + fixer + 이미지 prompt 검증
- domain/image_generation/CLAUDE.md — [9] Gemini 이미지 + 캐시 + 예산 가드
- domain/composer/CLAUDE.md — [10] 조립 + 네이버 HTML 화이트리스트
- tasks/todo.md — 현재 작업 체크리스트
- tasks/lessons.md — 실수 패턴 기록

## 변경 이력

- `2026-04-16`: 3계층 품질 강제, 물리 분석 정확도, Gemini 이미지, 의료법 안정화, 톤앤매너 전환, regression 테스트
- `2026-04-16`: CLAUDE.md 200줄 이내 리팩터링. 도메인별 규칙을 서브 CLAUDE.md로 분리, @reference 구조화
