"""BC-6: Gemini Nano Banana (gemini-2.5-flash-image) 이미지 생성 실측.

1회 호출로 SDK 동작 + 응답 시간 + 이미지 품질 + safety filter 확인.
"""
import hashlib
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

HERE = Path(__file__).parent
load_dotenv("config/.env")

API_KEY = os.environ.get("GEMINI_API_KEY")
assert API_KEY, "GEMINI_API_KEY not loaded"

# 의료 직접 키워드는 1회 차단 테스트로 남기고, 첫 호출은 안전한 일러스트로 시작
SAFE_PROMPT = (
    "A minimalist flat illustration of a traditional Korean herbal tea bowl "
    "with steam rising, warm beige and forest green color palette, "
    "editorial style, soft lighting, no text, no people, 1:1 aspect ratio"
)

MODEL_CANDIDATES = [
    "gemini-2.5-flash-image",
    "gemini-2.5-flash-image-preview",
    "gemini-2.0-flash-preview-image-generation",
]


def try_generate(client: genai.Client, model: str, prompt: str) -> tuple[bool, str, bytes | None]:
    """Return (ok, detail, image_bytes)."""
    try:
        start = time.time()
        resp = client.models.generate_content(model=model, contents=[prompt])
        elapsed = time.time() - start
    except Exception as e:
        return False, f"EXCEPTION: {type(e).__name__}: {str(e)[:200]}", None

    # 파싱: response.candidates[0].content.parts[i].inline_data
    try:
        cand = resp.candidates[0]
        finish = getattr(cand, "finish_reason", None)
        parts = cand.content.parts if cand.content else []
    except Exception as e:
        return False, f"PARSE_ERROR: {e}", None

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            mime = getattr(inline, "mime_type", "unknown")
            return (
                True,
                f"ok model={model} elapsed={elapsed:.2f}s mime={mime} finish={finish}",
                inline.data,
            )

    text = " ".join(getattr(p, "text", "") for p in parts if hasattr(p, "text"))
    return False, f"NO_IMAGE_IN_RESPONSE model={model} finish={finish} text={text[:200]}", None


def main() -> None:
    client = genai.Client(api_key=API_KEY)

    print("=== BC-6 Phase 1: 모델명 후보 탐색 ===")
    for model in MODEL_CANDIDATES:
        ok, detail, img = try_generate(client, model, SAFE_PROMPT)
        print(f"  [{model}]: {detail[:150]}")
        if ok:
            print(f"\n=== BC-6 Phase 2: 성공 모델 = {model} ===")
            out_path = HERE / "bc6-output.png"
            out_path.write_bytes(img)  # type: ignore
            print(f"  saved: {out_path.name} ({len(img)} bytes)")  # type: ignore

            # SHA256 캐시 키 일관성 확인
            h1 = hashlib.sha256((SAFE_PROMPT + model).encode()).hexdigest()
            h2 = hashlib.sha256((SAFE_PROMPT + model).encode()).hexdigest()
            print(f"  cache key consistency: {h1 == h2} ({h1[:16]}...)")
            return

    print("\n❌ 모든 모델 후보 실패. SDK/모델 이름 재검토 필요")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
