# Generation Domain

아웃라인 + 도입부 + 본문 생성. SPEC.md §3 [6][7] 구현. **M2 불변 규칙이 최상위**.

## 🔴 M2 — 절대 위반 불가

**`body_writer.py` 는 intro 원문을 받을 수 없다.**

- `generate_body()` 시그니처에 `intro_text`, `intro_md`, `full_intro`, `intro_content`, `intro_raw` 등 원문 파라미터 금지
- 유일 허용: `intro_tone_hint: str` — 도입부 톤 힌트 문자열 (짧은 설명)
- 프롬프트 문자열에도 도입부 원문 삽입 금지. 한글 "도입부" 리터럴도 프롬프트 안에 두지 말 것
- 최종 조립은 `composer/assembler.py` 가 `intro + body_sections` 프로그래매틱 concat
- `post-edit-lint.sh` 훅과 `seo-writer-guardian` 에이전트가 자동 차단

**이유**: 긴 본문 단일 호출 시 톤이 흔들린다. [6]에서 도입부를 먼저 확정해 "음성 샘플" 역할을 하게 하고, [7]은 그 톤만 이어받아 본문을 생성한다. [7]이 intro 원문을 보면 재생성 경향이 생겨 품질·비용 모두 손해.

## 단일 진입점: prompt_builder.py

- 모든 LLM 프롬프트는 `prompt_builder.py` 에서 빌드
- `outline_writer.py`, `body_writer.py` 는 f-string·템플릿으로 프롬프트 직접 조립 금지
- `build_outline_prompt()`, `build_body_prompt()` 만 호출
- 의료법 규칙 주입(1차 방어)은 `prompt_builder` 한 곳에서만 발생

## 핵심 규칙

- [6] 아웃라인 출력: 제목 + 섹션 구조 + 도입부 200~300자 + `suggested_tags` + **`image_prompts`**
- [7] 본문은 **2번째 섹션부터만** 생성. 도입부는 재생성하지 않음
- 모델: Opus 4.6 (두 단계 모두)
- LLM 호출은 `tool_use` 로 JSON 스키마 강제 (Pydantic → JSON schema)
- 중립화 프롬프트: 홍보성 소구 포인트를 일반 정보로 재서술 지시
- 태그 개수는 `round(avg_tag_count_per_post)` 분석값 그대로. 클램프 없음 (Naver 30개 상한만 예외)
- **이미지 prompt 개수**는 `round(image_pattern.avg_count_per_post)` 분석값 그대로. 예산 가드는 [9] 단계에서

## 이미지 prompt 생성 규칙 ([6] 단계)

`prompt_builder.build_outline_prompt` 가 LLM 에게 image_prompts 를 만들도록 지시할 때 다음 제약을 강제 주입한다:

- **언어: 영어** — Gemini Image 모델은 영어가 안정적
- **각 prompt 에 반드시 포함**: `no text` (또는 `no letters`) + 권장 스타일 1개 + 시나리오 + 색감
- **인물 등장 시 필수**: `Korean` 키워드 명시 (예: `Korean woman`, `Korean man`, `Korean person`, `Korean family`). 외국인 외형 금지
- **권장 시나리오** (한국적 맥락):
  - 한식 요리·식사, 한방 재료, 한국 자연·풍경
  - 라이프스타일 (요가, 산책, 명상, 차 마시기)
  - 한국인 일상 (운동복 입은 한국 여성, 식사하는 한국 가족 등)
- **권장 스타일**: `realistic photography`, `lifestyle photography`, `natural lighting`, `cinematic`, `high quality DSLR`, `flat illustration`, `minimalist infographic`, `food photography`
- **금지 키워드** (인물 유무 무관):
  - 환자: `patient`, `환자`, `injured`, `sick person`
  - 전후 비교: `before/after`, `comparison shot`, `weight loss progression`
  - 시술: `medical procedure`, `surgery`, `injection`
  - 신체 비교: `body comparison`, `naked`, `nude`
  - 효과 보장: `100%`, `guarantee`
- **종횡비**: 1024x1024

이 규칙은 [8] compliance + [9] image_generation 도메인이 한 번 더 검증한다. 3중 안전망.

## 파일 책임

- `prompt_builder.py` — **단일 프롬프트 진입점**
- `outline_writer.py` — [6] 아웃라인 + 도입부 생성 (Opus 4.6, tool_use)
- `body_writer.py` — [7] 본문 생성 (Opus 4.6, intro 미유입)
- `model.py` — `Outline`, `OutlineSection`, `BodyResult`, `SuggestedTags`, `ImagePromptDraft` Pydantic 모델

## 금지

- **body_writer 시그니처·프롬프트에 intro 원문 유입** (M2 위반, 자동 차단됨)
- `prompt_builder` 우회한 직접 프롬프트 조립
- 의료법 규칙 주입을 여러 파일에 분산
- 텍스트 프롬프트로 "JSON 답해" (반드시 `tool_use`)
- 태그 개수에 `[5, 15]` 같은 임의 클램프 적용

## 참조

- @../../SPEC.md §3 [6][7]
- @../../.claude/skills/generation/SKILL.md
- @../../.claude/agents/domain/seo-writer-guardian.md (M2 리뷰 전담)
- @../../.claude/hooks/post-edit-lint.sh (M2 자동 차단)
