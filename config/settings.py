"""환경 변수 로드. `config/.env` 단일 출처.

CLAUDE.md 의 "환경 변수는 config/settings.py 에서만 로드" 원칙을 강제한다.
다른 모듈에서 `os.environ` 직접 접근 금지. 반드시 `from config.settings import settings` 사용.

필드는 모두 Optional 로 선언 — 아직 세팅되지 않은 값으로 인한 import 실패 방지.
실제 사용 시점에서 `require()` 로 존재 검증.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Bright Data (크롤러 도메인)
    # Naver 는 SERP API 의 전용 엔진 목록에 없으므로 SERP 수집·본문 수집 모두
    # Web Unlocker 단일 zone 으로 처리한다. 자세한 사유는 tasks/lessons.md 참조.
    bright_data_api_key: str | None = Field(default=None, description="Bright Data API key")
    bright_data_web_unlocker_zone: str | None = Field(
        default=None, description="Web Unlocker zone name (네이버 SERP + 본문 공용)"
    )

    # Anthropic Claude (생성·분석·의료법 검증)
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")

    # Google Gen AI (이미지 생성 — Gemini 3.1 Flash Image Preview)
    gemini_api_key: str | None = Field(default=None, description="Google AI Studio API key")

    # Supabase (패턴 카드 저장소)
    supabase_url: str | None = Field(default=None, description="Supabase project URL")
    supabase_key: str | None = Field(default=None, description="Supabase service role key")

    # LLM 모델 식별자 (SPEC-SEO-TEXT.md §5 — 역할별 매핑)
    model_opus: str = "claude-opus-4-6"
    model_sonnet: str = "claude-sonnet-4-6"
    image_model: str = "gemini-2.5-flash-image"
    image_size: str = "1024x1024"

    # 파이프라인 동작 상수
    min_analyzed_samples: int = 7
    retry_max_attempts: int = 2
    llm_tool_use_timeout_seconds: int = 60

    # 이미지 생성 안전장치
    image_generation_budget_per_run: int = 30  # 분석 결과 그대로 반영, 실사용 상한 안전망
    image_cache_dir: str = "output/_image_cache"
    image_max_width: int = 720  # 네이버 블로그 본문 폭 기준 리사이즈
    image_jpeg_quality: int = 85  # JPEG 변환 품질 (1~100)


settings = Settings()


def require(field_name: str) -> str:
    """필수 문자열 설정값을 가져온다. None 이면 명시적 에러.

    호출 예: `require("bright_data_api_key")`
    """
    value = getattr(settings, field_name, None)
    if value is None:
        raise RuntimeError(
            f"설정 '{field_name}' 이(가) config/.env 에 없습니다. SPEC-SEO-TEXT.md §6 config/.env 참조."
        )
    if not isinstance(value, str):
        raise TypeError(f"설정 '{field_name}' 은(는) 문자열이어야 합니다.")
    return value
