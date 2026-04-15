---
name: image-generation
description: Google Gemini 3.1 Flash Image Preview 로 SEO 블로그용 AI 이미지를 생성한다. [6] 아웃라인에서 LLM 이 만든 image_prompts 를 [8] 의료법 검증 통과 후 실제 이미지로 변환한다. 영어 prompt, 텍스트 절대 금지, 인물 등장 시 한국인 명시 필수, 의료 맥락(환자/전후/시술/신체비교) 영구 금지. SHA256 캐시 + 예산 가드 + 1회 재시도. '이미지 생성', 'AI 이미지', 'Gemini 이미지', '이미지 prompt', '블로그 이미지' 요청 시 반드시 이 스킬을 사용할 것.
---

# Image Generation Skill — Gemini 3.1 Flash Image Preview

검증된 image_prompt 를 받아 실제 PNG 파일로 만든다. SPEC-SEO-TEXT.md §3 [9] 구현. 이 스킬은 `domain/image_generation/` 의 코드를 작성하거나 디버깅할 때 트리거된다.

## 책임 범위

- **포함**: Gemini 호출, 캐시 조회·저장, 예산 가드, 재시도, 결과 메타 저장
- **불포함**:
  - 이미지 prompt 자체 생성 (그건 [6] outline_writer 의 LLM 이 한다)
  - prompt 의 의료법 검증 (그건 [8] compliance 가 한다)
  - prompt 의 콘텐츠 적합성 판단 (이미 검증된 것만 받음)

## 환경 변수 (config/.env)

```
GEMINI_API_KEY=...
```

`config/settings.py` 에 다음 상수 있음:
- `image_model`: 기본 `"gemini-3.1-flash-image-preview"`
- `image_size`: 기본 `"1024x1024"`
- `image_generation_budget_per_run`: 기본 `10`
- `image_cache_dir`: 기본 `"output/_image_cache"`

## 호출 패턴

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.gemini_api_key)

response = client.models.generate_content(
    model=settings.image_model,
    contents=[image_prompt.prompt],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    ),
)

# 응답 파트에서 이미지 바이트 추출
png_bytes = None
for part in response.candidates[0].content.parts:
    if part.inline_data and part.inline_data.data:
        png_bytes = part.inline_data.data
        break

if png_bytes is None:
    raise ImageGenerationError("응답에 이미지 데이터 없음")
```

## 🔴 prompt 정합성 검증 (안전망)

[8] compliance 가 1차 차단하지만, image_generation 도메인이 한 번 더 검증한다. 다음 조건 하나라도 위반 시 `InvalidImagePromptError` 발생:

**필수 포함** (영어, 소문자 비교):
- `no text` 또는 `no letters` — Gemini 한글 깨짐 방지

**조건부 필수** (인물 등장 시):
- prompt 에 사람 관련 키워드 (`person`, `people`, `man`, `woman`, `face`, `portrait`, `family`, `child`) 가 있으면 → 반드시 `Korean` 키워드 동반
- 누락 시 `prompt mentions people but does not specify 'Korean'` 에러

**금지 키워드** (인물 유무 무관, 대소문자 무시):
- 환자: `patient`, `환자`, `injured`, `sick person`
- 전후 비교: `before/after`, `before and after`, `comparison shot`, `weight loss progression`
- 시술: `medical procedure`, `surgery`, `injection`, `treatment scene`
- 신체 비교: `body comparison`, `naked`, `nude`
- 효과 보장: `100%`, `guarantee`
- 특정 브랜드·업체명 — 별도 리스트는 `rules.py` 에 추가

위반 prompt 는 생성 호출 없이 skip 처리. `skipped` 메타에 `reason="prompt_safety_failed"` 기록.

## 캐싱 (필수)

비용 폭주 방지의 핵심.

```python
import hashlib
from pathlib import Path

cache_dir = Path(settings.image_cache_dir)
cache_dir.mkdir(parents=True, exist_ok=True)

key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
cached = cache_dir / f"{key}.png"

if cached.exists() and not regenerate:
    png_bytes = cached.read_bytes()  # 캐시 히트, API 호출 없음
else:
    png_bytes = call_gemini(prompt)
    cached.write_bytes(png_bytes)
```

`regenerate_images=True` 플래그 시에만 캐시 무시.

## 예산 가드

```python
budget = settings.image_generation_budget_per_run  # 10
generated_count = 0
for prompt in image_prompts:
    if generated_count >= budget:
        skipped.append({"sequence": prompt.sequence, "reason": "budget_exceeded"})
        continue
    # ... 생성 ...
    generated_count += 1
```

캐시 히트는 budget 카운트에 포함하지 않는다 (실제 API 호출이 아니므로).

## 재시도

- API 호출 실패 (네트워크, 5xx, 타임아웃) → 1초 대기 후 1회 재시도
- 2회 모두 실패 → `skipped` 에 `reason="api_error"` 기록, 다음 prompt 진행
- **파이프라인 전체 실패로 이어지지 않음** (이미지 1개 누락은 허용)

## 출력 메타

`output/{slug}/{timestamp}/images/index.json`:

```json
{
  "model": "gemini-3.1-flash-image-preview",
  "generated_count": 4,
  "skipped_count": 1,
  "cache_hits": 2,
  "api_calls": 2,
  "generated": [
    {
      "sequence": 1,
      "path": "images/image_1.png",
      "prompt_hash": "abc123...",
      "alt_text": "건강한 한식 재료",
      "from_cache": false
    },
    {
      "sequence": 2,
      "path": "images/image_2.png",
      "prompt_hash": "def456...",
      "alt_text": "체질 분석 개념도",
      "from_cache": true
    }
  ],
  "skipped": [
    {"sequence": 3, "reason": "compliance_failed"},
    {"sequence": 4, "reason": "api_error"}
  ]
}
```

## composer 와의 인터페이스

[10] composer 의 `outline_md.py` 가 `images/index.json` 을 읽어 `outline.md` 의 "이미지 삽입 가이드" 섹션에 매핑 추가:

```markdown
## 이미지 삽입 가이드 (수동)

1. **위치**: 도입부 직후
   - **파일**: `images/image_1.png`
   - **alt**: 건강한 한식 재료

2. **위치**: 섹션 3 끝
   - **파일**: `images/image_2.png`
   - **alt**: 체질 분석 개념도

3. **위치**: 결론 직전 — ⚠️ 생성 실패 (api_error)
```

본문 (.md/.html) 에는 이미지 마커 미삽입 — 사용자가 네이버 에디터에서 수동 업로드.

## 금지 사항

- 검증 안 된 prompt 로 generate 호출
- prompt 에 한글 (모두 영어)
- 캐시 위치를 코드에 하드코딩
- 이미지에 텍스트 후처리 삽입
- API 실패를 raise 해서 파이프라인 종료 (스킵으로 처리)
- `print()` 사용 (`logging` 만)

## 테스트 체크리스트

- [ ] `validate_prompt()` 가 `no text` 누락된 prompt 를 거부하는가
- [ ] 캐시 히트 시 API 호출이 0 회인가 (mock 으로 검증)
- [ ] 예산 초과 시 나머지 prompt 가 skip 되는가
- [ ] API 실패 1회 → 재시도 → 성공 흐름이 동작하는가
- [ ] API 실패 2회 → 해당 이미지 skip + 파이프라인 계속이 동작하는가
- [ ] `index.json` 메타가 generated/skipped 모두 기록하는가
