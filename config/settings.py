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

    # 네이버 검색광고 API (키워드도구 - 월간 검색량 조회)
    # 발급: searchad.naver.com → 도구 → API 사용 관리. HMAC SHA256 서명 필요.
    # 무료 + 분 60회 호출 한도. 비용 0 이지만 호출 횟수는 record_usage 로 추적.
    naver_ad_api_key: str | None = Field(default=None, description="검색광고 라이선스 키")
    naver_ad_secret_key: str | None = Field(default=None, description="HMAC 서명용 시크릿")
    naver_ad_customer_id: str | None = Field(default=None, description="광고주 ID (Customer ID)")

    # LLM 모델 식별자 (SPEC-SEO-TEXT.md §5 — 역할별 매핑)
    # 창작 — [6] 아웃라인·도입부·image_prompts 는 Opus 유지.
    # [7] 본문 초안은 Sonnet 으로 내리고 약한 섹션만 Opus 로 보정 (하이브리드).
    model_opus: str = "claude-opus-4-7"
    # 에디터 ([7-후] 약한 섹션 보강, [8] 문단 재생성) — 본문 초안을 Sonnet 으로
    # 낮췄기 때문에 여기서는 Opus 로 상향해 "약한 섹션만 고급 모델로 보정" 한다.
    model_editor: str = "claude-opus-4-7"
    # 분류·검증 ([4a][4b] 추출, [7] 본문 초안, [8] LLM 검증, [8] 이미지 prompt 재생성)
    model_sonnet: str = "claude-sonnet-4-6"
    image_model: str = "gemini-2.5-flash-image"
    image_size: str = "1024x1024"

    # Extended Thinking — [6] 아웃라인 사고 예산. 0 이면 비활성 (기본값).
    # outline_writer 는 thinking 활성 시 tool_choice=auto + 프롬프트 강제 + tool_use
    # 누락 시 1회 재시도 패턴으로 Anthropic 제약을 우회한다.
    # 복잡 제약 동시 충족(SEO·의료법·톤·DIA·키워드 밀도)에 효과적이지만 비용이 크다.
    # 실측상 thinking off + `_assert_required_fields` + outline_validator 폴백이
    # 품질을 충분히 잡아내므로 기본값은 0. 품질 저하 확인 시 env 로 복원.
    outline_thinking_budget: int = 0

    # 웹 UI
    cors_origins: str = "http://localhost:3000"  # 쉼표 구분 복수 origin
    admin_api_key: str | None = Field(
        default=None,
        description="웹 API 보호용. None이면 인증 비활성(개발 모드), 설정 시 X-API-Key 헤더 필수",
    )
    job_timeout_seconds: int = 3600  # 단일 파이프라인 실행 상한

    # Supabase Storage (결과물 영속화 — Render 컨테이너 파일시스템 휘발 대응)
    storage_bucket: str = "results"

    # 브랜드 sources presigned upload (Vercel 함수 4.5MB 페이로드 한계 우회)
    # 흐름: 프론트 → /sources/init → Supabase Storage signed URL → PUT 직접 → /sources/confirm
    brand_sources_bucket: str = "brand-sources"
    brand_sources_max_bytes: int = 50 * 1024 * 1024  # 50 MB
    brand_sources_signed_url_ttl_seconds: int = 300  # 5 분
    # parser 단계와 일치 — domain/brand_card/source_parser.py _SUPPORTED_EXTENSIONS
    brand_sources_allowed_suffixes: tuple[str, ...] = (
        ".txt",
        ".md",
        ".docx",
        ".pdf",
        ".html",
        ".htm",
    )

    # 브랜드 미디어 자산 (실사 사진 라이브러리) presigned upload — 동일 패턴
    brand_media_bucket: str = "brand-media"
    brand_media_max_bytes: int = 20 * 1024 * 1024  # 20 MB (이미지)
    brand_media_allowed_suffixes: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    )

    # API 비용 (USD per 1M tokens, 2026-04 기준)
    cost_anthropic_opus_input: float = 15.0
    cost_anthropic_opus_output: float = 75.0
    # 에디터는 Opus 4.7 기준 (하이브리드: 약한 섹션만 고급 모델로 보정).
    # model_editor 를 바꾸면 이 단가도 동기화.
    cost_anthropic_editor_input: float = 15.0
    cost_anthropic_editor_output: float = 75.0
    cost_anthropic_sonnet_input: float = 3.0
    cost_anthropic_sonnet_output: float = 15.0
    cost_gemini_image_per_request: float = 0.04
    cost_brightdata_per_request: float = 0.01

    # 이미지 생성 안전장치
    image_generation_budget_per_run: int = 15  # 실사용 상한 안전망 (평균 8~10장 사용)
    image_parallel_workers: int = 5  # Gemini 병렬 워커 수 (레이트리밋 고려 5~8)
    image_cache_dir: str = "output/_image_cache"
    image_max_width: int = 720  # 네이버 블로그 본문 폭 기준 리사이즈
    image_jpeg_quality: int = 85  # JPEG 변환 품질 (1~100)

    # 브랜드 카드 — AI 이미지 예산 (R1 카드 세트당 호출 상한)
    brand_card_image_budget_per_set: int = 6  # 카드 세트당 Gemini 호출 상한

    # 순위 추적 (SPEC-RANKING.md). 운영은 외부 cron(GitHub Actions) 이 정식 경로.
    # in-process APScheduler 는 컨테이너 재시작에 취약 (2026-04-30/05-01 누락 사고).
    # 로컬 개발자가 in-process 스케줄러로 실험할 때만 RANKING_SCHEDULER_ENABLED=true.
    ranking_scheduler_enabled: bool = False
    ranking_scheduler_hour: int = 9  # KST 매일 실행 시각 (in-process 모드 한정)
    ranking_scheduler_minute: int = 0
    # publication 간 대기 (Bright Data rate 보호)
    ranking_check_sleep_seconds: float = 1.0

    # 키워드 난이도 분석 속도 튜닝 (Phase F 후속, 2026-05-04).
    # 8/0.3 → 12/0.2 로 상향, BrightData 분당 한도 (실측) 안에서 추가 성능 확보.
    # 운영 중 4xx 발생 시 env 로 즉시 하향 (코드 수정 없이 보정 가능).
    keyword_difficulty_batch_parallel: int = Field(
        default=12, description="키워드 배치 분석 동시 worker 수"
    )
    keyword_difficulty_batch_rate_seconds: float = Field(
        default=0.2, description="배치 worker 당 호출 후 sleep (초)"
    )
    # SERP 캐시 — TTL 30 → 60 분으로 상향. 같은 키워드 재분석 시 BrightData 호출 절감.
    # SERP 변동 빈도 대비 60 분은 안전 (네이버 SERP 는 실시간성보다 안정성에 가까움).
    keyword_difficulty_cache_ttl_seconds: int = Field(
        default=3600, description="SERP HTML 메모리 캐시 TTL (초)"
    )
    keyword_difficulty_cache_max_entries: int = Field(
        default=256, description="LRU 캐시 최대 항목 수"
    )


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
