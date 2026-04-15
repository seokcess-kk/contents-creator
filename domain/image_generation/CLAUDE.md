# Image Generation Domain

[9] 단계 — 검증된 `image_prompts` 를 Gemini 3.1 Flash Image Preview 로 실제 이미지로 만든다. SPEC.md §3 [9] 구현.

## 🔴 최상위 원칙

1. **검증되지 않은 prompt 호출 금지** — [8] compliance 통과한 것만 받는다
2. **이미지에 텍스트 절대 금지** — prompt 에 `no text`, `no letters`, `no captions` 강제. 모든 prompt 는 이 키워드 포함 검증
3. **인물은 한국인만** — 사람·얼굴·실사 인물 사진 허용. 단, prompt 에 사람 관련 키워드가 등장하면 반드시 `Korean` 키워드 동반. 외국인·서양인 외형 묘사 금지
4. **의료 맥락 영구 금지** — 인물 유무 무관 다음 항상 금지: 환자(`patient`/`환자`), 전후 비교(`before/after`), 시술 장면(`medical procedure`/`surgery`/`injection`), 신체 비교(`body comparison`/`naked`/`weight loss progression`), 효과 보장(`100%`/`guarantee`)
5. **캐싱으로 비용 폭주 방지** — prompt 해시 기반 파일 캐시. 같은 prompt 재실행 시 무료
6. **예산 가드** — `IMAGE_GENERATION_BUDGET_PER_RUN` 초과 시 나머지 prompt 스킵 (실패 아님)
7. **API 실패는 스킵, 파이프라인은 계속** — 이미지 1개 실패가 전체 실패로 이어지지 않음

## 파일 책임

- `model.py` — `ImagePrompt`, `GeneratedImage`, `ImageGenerationReport` Pydantic 모델
- `provider.py` — `ImageProvider` Protocol + `GeminiImageProvider` 구현
- `prompt_builder.py` — 이미지 prompt 빌드용 헬퍼 (검증 키워드 자동 부착). 단, prompt 자체는 generation 도메인의 outline_writer 가 LLM 으로 만든다 — 이 파일은 정합성 검증·정규화만
- `cache.py` — SHA256 해시 기반 파일 캐시 (`output/_image_cache/{hash}.png`)
- `generator.py` — `generate_images(prompts, dest_dir, reporter) -> ImageGenerationReport` 메인 진입점

## 호출 패턴 (Google Gen AI SDK)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.google_api_key)

response = client.models.generate_content(
    model=settings.image_model,  # "gemini-3.1-flash-image-preview"
    contents=[image_prompt.prompt],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    ),
)

# 이미지 바이트 추출
for part in response.candidates[0].content.parts:
    if part.inline_data and part.inline_data.data:
        png_bytes = part.inline_data.data
        break
```

## prompt 정합성 검증 (prompt_builder.py)

`ImageProvider.generate(prompt)` 호출 직전에 다음을 확인:

```python
PEOPLE_KEYWORDS = ("person", "people", "man", "woman", "face", "portrait", "family", "child")

FORBIDDEN_KEYWORDS = (
    # 환자
    "patient", "환자", "injured", "sick person",
    # 전후 비교
    "before/after", "before and after", "comparison shot", "weight loss progression",
    # 시술 장면
    "medical procedure", "surgery", "injection", "treatment scene",
    # 신체 비교
    "body comparison", "naked", "nude",
    # 효과 보장
    "100%", "guarantee",
)


def validate_prompt(prompt: str) -> None:
    p = prompt.lower()

    # 1. 텍스트 금지 키워드 필수
    if "no text" not in p and "no letters" not in p:
        raise InvalidImagePromptError("prompt must contain 'no text' or 'no letters'")

    # 2. 인물 등장 시 'Korean' 명시 필수
    if any(kw in p for kw in PEOPLE_KEYWORDS):
        if "korean" not in p:
            raise InvalidImagePromptError(
                "prompt mentions people but does not specify 'Korean'"
            )

    # 3. 의료 맥락·금지 키워드 차단
    for kw in FORBIDDEN_KEYWORDS:
        if kw in p:
            raise InvalidImagePromptError(f"prompt contains forbidden keyword '{kw}'")
```

[8] compliance 가 1차 차단하지만, image_generation 도메인의 안전망으로 한 번 더.

## 캐시 (cache.py)

```python
import hashlib
from pathlib import Path

def cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

def get_cached(prompt: str, cache_dir: Path) -> bytes | None:
    path = cache_dir / f"{cache_key(prompt)}.png"
    if path.exists():
        return path.read_bytes()
    return None

def store(prompt: str, png_bytes: bytes, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{cache_key(prompt)}.png"
    path.write_bytes(png_bytes)
```

`regenerate_images=True` 플래그 시 캐시 무시.

## 예산 가드

```python
budget = settings.image_generation_budget_per_run  # 기본 10
if generated_count >= budget:
    logger.warning("image budget exceeded, skipping remaining prompts")
    skipped.append({"sequence": p.sequence, "reason": "budget_exceeded"})
    continue
```

## 재시도

- API 호출 실패 시 1회 재시도 (1초 대기)
- 2회 후도 실패 → 해당 이미지 스킵 (`reason: "api_error"`), 파이프라인 계속

## 출력

- 이미지 파일: `output/{slug}/{timestamp}/images/image_{sequence}.png`
- 메타: `output/{slug}/{timestamp}/images/index.json`
  ```json
  {
    "generated": [{"sequence": 1, "path": "images/image_1.png", "prompt_hash": "...", "alt_text": "..."}],
    "skipped": [{"sequence": 3, "reason": "compliance_failed"}]
  }
  ```
- 반환: `ImageGenerationReport(generated, skipped, total_cost_estimate)`

## 금지 사항

- 검증 실패한 prompt 로 generate 호출
- prompt 에 한글 텍스트 (모든 prompt 영어)
- 캐시 위치 하드코딩 (`settings.image_cache_dir` 사용)
- 이미지 후처리로 텍스트 삽입
- API 호출 실패 시 파이프라인 전체 종료 (스킵으로 처리)
- `print()` 디버깅 (logging 사용)

## 참조

- @../../SPEC.md §3 [9]
- @../../.claude/skills/image-generation/SKILL.md
- @../compliance/CLAUDE.md (이미지 prompt 검증 규칙)
