# Compliance Domain

의료광고법 3중 방어. SPEC-SEO-TEXT.md §3 [8] 구현.

## 🔴 최상위 원칙: rules.py 단일 출처

**금지 표현·8개 카테고리 정의는 `rules.py` 외부에 둘 수 없다.**

- `checker.py`, `fixer.py`, `domain/generation/prompt_builder.py` 는 `from .rules import ...` 참조만
- 새 위반 패턴 발견 시 `rules.py` 에만 추가
- `post-edit-lint.sh` 훅도 `rules.py` 의 `FORBIDDEN_LITERALS` 를 동적 로드해 검사
- 문서·주석·스킬 파일도 예시로 금지 표현을 쓸 수 있지만, 실제 런타임 로직에서 참조되는 유일한 소스는 `rules.py`

## 3중 방어 완결성

- **1차 (사전 주입)** — `prompt_builder` 가 [6][7] 프롬프트에 금지 규칙 주입. `build_outline_prompt()`, `build_body_prompt()` 가 `compliance_rules: ComplianceRules` 파라미터를 받아 프롬프트에 실제 삽입
- **2차 (사후 검증)** — `checker.py` 가 규칙 기반 1차 스크리닝 + LLM 검증 2단계 모두 실행 (둘 다 필요)
- **3차 (자동 수정)** — `fixer.py` 가 위반 교정 후 `checker` 재검증. 최대 **2회** 반복

## Fixer 동작 원칙

1. **기본: 구절 치환 (phrase replacement)** — 위반 표현 자리만 안전 대체어로 교체. 주변 문맥·톤 보존, 빠르고 안전. 대부분의 케이스가 이것으로 해결
2. **폴백: 해당 문단만 재생성** — 치환 결과가 LLM 자연스러움 검사 실패 시에만. **도입부는 재생성 대상 아님** (M2 톤 락 유지). 도입부가 위반이면 치환만 시도하고 실패 시 파이프라인 실패 종료
3. **전체 본문 재생성 절대 금지** — 항상 국소 수정

## 핵심 규칙

- 8개 카테고리는 사용자 확정 전까지 `rules.py` 의 `ViolationCategory` enum 에 placeholder 로 예약
- **카테고리 임의 추가·삭제 금지**. 변경은 SPEC-SEO-TEXT.md §5 수정 동반 필요
- 재시도는 최대 2회. `while True:` 무한 루프 금지
- 검증 결과는 `ComplianceReport` Pydantic 모델로 반환. 실패를 `raise` 가 아닌 `ComplianceReport(passed=False)` 로 처리
- 태그(`suggested_tags`)도 검증 대상. 위반 태그는 유사어 교체 또는 목록에서 제거
- **이미지 prompt(`image_prompts`) 도 검증 대상**. 위반 prompt 는 fixer 가 안전한 대안으로 재생성, 2회 후 실패 시 해당 슬롯 스킵
- 모델: Sonnet 4.6, `tool_use` 로 구조화 출력

## 이미지 prompt 검증 추가 규칙

- **필수 포함 (항상)**: `no text` 또는 `no letters` (Gemini 한글 깨짐 방지)
- **조건부 필수 (인물 등장 시)**: prompt 에 사람 키워드 (`person`, `people`, `man`, `woman`, `face`, `portrait`, `family`, `child`) 가 있으면 → 반드시 `Korean` 동반. 누락 시 fixer 가 `Korean` 추가
- **금지 키워드** (인물 유무 무관 영구 금지):
  - 환자: `patient`, `환자`, `injured`, `sick person`
  - 전후 비교: `before/after`, `before and after`, `comparison shot`, `weight loss progression`
  - 시술: `medical procedure`, `surgery`, `injection`, `treatment scene`
  - 신체 비교: `body comparison`, `naked`, `nude`
  - 효과 보장: `100%`, `guarantee`
- **rules.py 의 일반 금지 표현**도 prompt·alt_text 양쪽에 적용 (단일 출처 원칙)
- 위반 시 fixer 는 안전한 대체 prompt 를 LLM 에게 재요청. 2회 시도 후 실패 → `ComplianceReport.image_skipped` 에 sequence 기록 (파이프라인 종료 X)

## 파일 책임

- `rules.py` — **단일 출처**. `ViolationCategory` enum, `FORBIDDEN_LITERALS` 리스트, regex 패턴, LLM 지시문
- `checker.py` — 규칙 스크리닝 + LLM 검증 + 재검증 루프
- `fixer.py` — 구절 치환 + 폴백 문단 재생성
- `model.py` — `ComplianceReport`, `Violation`, `Changelog` Pydantic 모델

## 금지

- `rules.py` 외부에서 금지 표현 하드코딩 (훅이 자동 차단)
- 8개 카테고리 임의 확장·축소
- 3회 이상 재시도
- 본문 전체 재생성
- 규칙 기반만으로 "통과" 판정 (LLM 검증도 필수)
- LLM 검증만으로 "통과" 판정 (규칙 기반도 필수)
- 검증 실패를 예외로 처리 (데이터로 반환)

## 참조

- @../../SPEC-SEO-TEXT.md §3 [8]
- @../../.claude/skills/medical-compliance/SKILL.md
- @../../.claude/agents/domain/compliance-reviewer.md
