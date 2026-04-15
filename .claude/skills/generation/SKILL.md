---
name: generation
description: 패턴 카드 기반으로 SEO 원고를 생성한다. [6]에서 아웃라인과 도입부(200~300자)를 동시 확정한 뒤, [7]에서 2번째 섹션부터 본문을 생성한다. body_writer는 intro 원문을 절대 받지 않는다. 홍보성 상위글의 소구 포인트는 중립적 정보로 재서술한다. '아웃라인 작성', '본문 생성', 'SEO 원고 작성', '원고 생성' 요청 시 반드시 이 스킬을 사용할 것.
---

# Generation Skill — Outline + Body (Tone-Lock Pattern)

패턴 카드를 프롬프트로 변환해 SEO 원고를 생성한다. SPEC-SEO-TEXT.md §3 [6][7]을 구현한다.

## 2단계 구조

| 단계 | 파일 | 모델 | 출력 |
|---|---|---|---|
| [6] 아웃라인 + 도입부 확정 | `outline_writer.py` | Opus 4.6 | 제목 + 섹션 구조 + 도입부 본문 200~300자 |
| [7] 본문 생성 (섹션 2~N) | `body_writer.py` | Opus 4.6 | 2번째 섹션부터의 본문 (intro 제외) |

## 🔴 최상위 원칙: M2 — body_writer는 intro 원문을 받지 않는다

**이유:** LLM은 긴 본문을 단일 호출로 생성하면 중간에 톤이 흔들린다. [6]에서 도입부를 짧게 확정하면 그게 "음성 샘플"이 되어 [7] 본문의 톤이 안정된다. 단, [7]이 intro 원문을 보면 재생성하려는 경향이 있어 품질·경제성 모두 손해. **intro 원문은 [7] 프롬프트에 절대 포함되지 않는다.**

### 코드 구조로 강제

```python
# body_writer.py
def generate_body(
    outline_without_intro: Outline,   # sections[0]이 is_intro=True 인 섹션은 제외된 상태
    intro_tone_hint: str,             # 예: "공감형 도입부가 이미 작성됨. 친근한 톤 유지"
    pattern_card: PatternCard,
) -> BodyResult:
    ...
```

`intro_text`, `full_intro`, `intro_md` 같은 이름의 파라미터는 이 함수에 존재할 수 없다. `domain/generation/body_writer.py`에 `intro`나 `도입부` 문자열이 등장하면 `seo-writer-guardian` 에이전트와 `post-edit-lint.sh` 훅이 차단한다.

### 최종 조립은 composer가 수행

`domain/composer/assembler.py`가 `intro_text + body_sections` 를 프로그래매틱 concat. LLM이 concat하지 않는다.

## 단일 진입점: prompt_builder.py

모든 LLM 프롬프트는 `domain/generation/prompt_builder.py`에서 빌드한다. `outline_writer.py`, `body_writer.py`는 직접 프롬프트 문자열을 조립하지 않는다.

```python
# prompt_builder.py
def build_outline_prompt(pattern_card: PatternCard, compliance_rules: ComplianceRules) -> PromptMessages: ...
def build_body_prompt(outline_without_intro: Outline, intro_tone_hint: str, pattern_card: PatternCard, compliance_rules: ComplianceRules) -> PromptMessages: ...
```

단일 진입점 이유:
- 의료법 규칙 주입을 한 곳에서 관리 (1차 방어)
- 중립화 지시를 한 곳에서 관리
- 프롬프트 변경의 영향 범위 명확화

## [6] 아웃라인 + 도입부 생성

### 프롬프트 핵심 섹션

```
[시스템]
너는 네이버 블로그 SEO 전문 콘텐츠 기획자다.
특정 업체를 홍보하거나 광고하는 내용을 포함하지 않는다.
중립적 정보 콘텐츠를 작성한다.

[상위 글 구조 — 패턴 카드 기반]
필수 섹션: {required}
빈출 섹션: {frequent}
차별화 가능 (0~2개 선택): {differentiating}
top 구조 시퀀스: {top_structures}

[타겟 독자]
고민: {concerns}
검색 의도: {search_intent}
정보 수준: {expertise_level}

[구조 규칙]
총 글자수: {min}~{max}
소제목: {subtitle_count}개
도입 방식: {선택된 intro_type}

[DIA+ 요소 지시]
표 {if table_ratio > 0.5: 1개 이상}
Q&A {if qa_ratio > 0.5: 포함}
리스트 {if list_ratio > 0.7: 2개 이상}
통계 {if stats_ratio > 0.5: 최소 2회}

[키워드]
주: {main_keyword}, 목표 밀도: {target_density}, 소제목 포함율: {subtitle_keyword_ratio}
연관: {related_keywords}

[소구 포인트 중립화]
아래는 상위 글에서 공통적으로 강조하는 가치다.
업체 주체가 아닌 일반화된 정보로 재서술하라.
- 공통 소구 포인트: {aggregated_appeal_points.common}

[SEO 태그 제안]
상위 글 공통 태그(80%+): {aggregated_tags.common}
빈출 태그(50%+): {aggregated_tags.frequent}
평균 태그 개수: {aggregated_tags.avg_tag_count_per_post}

`suggested_tags` 필드에 태그 리스트를 출력. 개수는 **분석 결과 그대로** 따른다:
- target = `round(avg_tag_count_per_post)` — 상위 글 평균 그대로. 별도 클램프 없음
- Naver 물리적 상한(30개)만 예외 처리
- 채우는 순서: (a) common 태그 전부 → (b) frequent 태그에서 본 원고 주제와 관련도 높은 순 → (c) 주 키워드·연관 키워드 중 top_tags에 없는 1~2개
- 중복 제거, 의료법 금지 표현 배제
- 태그는 공백 없는 단일 단어 또는 짧은 구 (예: `다이어트`, `한의원`, `체질분석`)

[의료법 사전 규칙 — 1차 방어]
{compliance_rules.pre_generation_injection}

[출력 지시]
1. 제목 1개
2. 섹션 N개 (필수 + 빈출 선택 + 차별화 0~2)
   - 각 섹션: subtitle, role, summary, target_chars, dia_markers
3. 도입부 본문 200~300자 (확정본, 본문 생성에서 재생성되지 않음)
4. keyword_plan (주 키워드 목표 횟수, 소제목 포함 목표)
```

### 구조화 출력 (tool_use)

```python
tools = [{
    "name": "record_outline",
    "input_schema": OutlineSchema,  # Pydantic → JSON schema
}]
```

## [7] 본문 생성

### 프롬프트 핵심

```
[시스템]
아래 아웃라인(2번째 섹션부터)을 기반으로 본문을 작성한다.
도입부는 이미 작성되어 있으므로 다시 작성하지 않는다.
중립적 정보 콘텐츠로 서술한다.

[톤 힌트]
도입부 훅 유형: {hook_type}
동일한 톤을 이어가라. 공감형이면 친근·공감 유지. 통계형이면 수치 기반 서술 유지.

[아웃라인 (섹션 2~N)]
{sections[1:]}

[키워드 배치 규칙]
주 키워드 "{main_keyword}":
  - 소제목 {subtitle_inclusion_target}% 이상 포함
  - 전체 밀도 {target_density}
연관 키워드: {related_keywords} — 자연스럽게 분산
일반화 부사("일반적으로", "보통", "대부분") 단락당 1회 이내

[문단 규칙]
문단당 {avg_chars}자 내외
짧은 문단 {short_ratio}% 적절히

[DIA+ 요소 삽입 지시]
{마커별 구체 지시}

[금지]
- 업체명/브랜드명 언급 금지
- "저희", "우리 병원" 등 1인칭 금지
- CTA(예약·전화·상담) 표현 금지
- 의료법 금지 표현: {8개 카테고리 요약}
- 도입부 재작성 금지 (이미 완료됨)
- **리스트 중첩 금지** (네이버 스마트에디터가 중첩 ul/ol 을 평탄화/소실시키므로 항상 평면 리스트만 출력. 하위 분류가 필요하면 별도 섹션·소제목으로 분리)

[출력 지시]
각 섹션을 순서대로 생성. 도입부 생성하지 말 것.
```

### 구조화 출력

```json
{
  "body_sections": [
    {"index": 2, "subtitle": "...", "content_md": "..."},
    {"index": 3, "subtitle": "...", "content_md": "..."}
  ]
}
```

## 테스트 체크리스트

- [ ] `body_writer.generate_body()` 시그니처에 intro 원문 파라미터가 없는가
- [ ] `build_body_prompt()`가 intro 원문을 프롬프트 문자열에 포함하지 않는가
- [ ] `domain/generation/` 전체 grep에서 `intro_text`, `intro_md` 같은 식별자가 body 경로에 없는가
- [ ] prompt_builder가 모든 프롬프트의 단일 진입점인가 (직접 f-string 조립 금지)
- [ ] Pydantic → tool_use JSON schema 변환이 정확한가
- [ ] 의료법 규칙 주입이 prompt_builder 한 곳에서만 발생하는가

## 금지 사항

- **body_writer 프롬프트 혹은 함수 시그니처에 intro 원문 유입 절대 금지** (M2 위반)
- prompt_builder를 우회한 프롬프트 직접 조립 금지
- 의료법 규칙 주입을 여러 파일에 분산 금지 (prompt_builder 단독 책임)
- tool_use 없이 "JSON으로 답해" 프롬프트만으로 구조화 출력 기대 금지
