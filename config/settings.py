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
    # 창작 ([6] 아웃라인·도입부·image_prompts, [7] 본문) — SEO 성과 최대 지렛대
    model_opus: str = "claude-opus-4-7"
    # 에디터 ([7-후] 약한 섹션 보강, [8] 문단 재생성) — 품질 하한선 상승
    model_editor: str = "claude-opus-4-7"
    # 분류·검증 ([4a][4b] 추출, [8] LLM 검증, [8] 이미지 prompt 재생성)
    model_sonnet: str = "claude-sonnet-4-6"
    image_model: str = "gemini-2.5-flash-image"
    image_size: str = "1024x1024"

    # Extended Thinking — [6] 아웃라인 사고 예산. 0 이면 비활성.
    # 복잡한 제약 동시 충족(SEO+의료법+톤+DIA+키워드) 에 유효.
    outline_thinking_budget: int = 2000

    # 파이프라인 동작 상수
    min_analyzed_samples: int = 7
    retry_max_attempts: int = 2
    llm_tool_use_timeout_seconds: int = 60

    # 웹 UI
    cors_origins: str = "http://localhost:3000"  # 쉼표 구분 복수 origin
    admin_api_key: str | None = Field(
        default=None,
        description="웹 API 보호용. None이면 인증 비활성(개발 모드), 설정 시 X-API-Key 헤더 필수",
    )
    job_timeout_seconds: int = 3600  # 단일 파이프라인 실행 상한

    # API 비용 (USD per 1M tokens, 2026-04 기준)
    cost_anthropic_opus_input: float = 15.0
    cost_anthropic_opus_output: float = 75.0
    # 에디터는 기본적으로 model_opus 와 동일 모델 (Opus 4.7) 가정. 다른 모델로
    # 분기할 경우 단가도 따로 설정.
    cost_anthropic_editor_input: float = 15.0
    cost_anthropic_editor_output: float = 75.0
    cost_anthropic_sonnet_input: float = 3.0
    cost_anthropic_sonnet_output: float = 15.0
    cost_gemini_image_per_request: float = 0.04
    cost_brightdata_per_request: float = 0.01

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
