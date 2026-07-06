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
    # Naver 는 SERP API 의 전용 엔진 목록에 없으므로 SERP 수집은 Web Unlocker 단일 zone
    # 으로 처리한다. 본문 수집은 기본 insane(curl-only) 우선 + Bright Data 폴백 하이브리드
    # (crawler_body_fetcher 참조) — 폴백용으로 이 키는 여전히 필수. 사유: tasks/lessons.md.
    bright_data_api_key: str | None = Field(default=None, description="Bright Data API key")
    bright_data_web_unlocker_zone: str | None = Field(
        default=None, description="Web Unlocker zone name (SERP + 본문 폴백 공용)"
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
    # 경량 분류·추출 — Intent 추출 등 단순 작업. Sonnet 대비 ~1/3, Opus 대비 ~1/15 비용.
    # 1차 적용: P1 Intent 축 (사용자 진짜 질문 2~5개 추출).
    model_haiku: str = "claude-haiku-4-5-20251001"
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

    # Title validator (domain/generation/title_validator.py)
    # default False — 의료법 위반은 logger.warning 만, 재생성 트리거 안 함.
    # True 시 strict 모드로 의료법 위반도 hard fail 처리 → outline 1회 재생성 트리거.
    # 의료 외 도메인 false positive ("최초", "1등", "반드시") 폭발 방지 위해 default off.
    title_validator_strict_compliance: bool = False

    # Polish Pack P4: title_validator 형태소 매칭 임계값 (recall = keyword 명사 set 크기 분모).
    # default 0.7 — keyword 명사 70% 이상이 title 명사에 포함되면 매칭 (kiwipiepy 사용).
    # 운영 데이터 누적 후 조정 (false positive 와 false negative trade-off).
    title_validator_morpheme_threshold: float = 0.7

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
    # Haiku 4.5 (2026-04 기준). 단순 분류·추출 모듈 (P1 Intent 등) 비용 추적용.
    cost_anthropic_haiku_input: float = 1.0
    cost_anthropic_haiku_output: float = 5.0
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

    # 키워드 배치 운영 (SPEC-BATCH.md). Phase 1 in-process worker pool.
    # 단일 JobManager(MAX_WORKERS=2) 와 분리 — 배치는 백그라운드, 단일은 즉시.
    # BrightData 동시성과 합산해 brightdata_concurrent_limit 안에 들어가야 함.
    batch_max_workers: int = Field(default=2, description="배치 worker pool 크기")
    # BrightData fetch 전역 동시성 한도 — 단일 + 배치 합산. 단일 프로세스 안전망.
    # 4xx 폭발 시 env 로 즉시 하향. 멀티 워커 진입 시 Redis advisory lock 으로 교체.
    brightdata_concurrent_limit: int = Field(
        default=5, description="BrightData fetch 동시 호출 한도 (단일 프로세스)"
    )

    # 하이브리드 본문 fetcher (vendor/insane_search — insane-search v0.9.1 curl-only).
    # 본문 수집 경로 라우팅 토글 (PR4). "insane" = 하이브리드(본문 insane + Bright Data
    # 폴백), "brightdata" = Bright Data 강제 단독(롤백 밸브 — 코드 변경 없이 env 로 즉시
    # 전환). ⚠️ 이 토글은 본문([2] page_scraping) 경로에만 적용된다. SERP 수집·
    # keyword_difficulty·ranking 은 값과 무관하게 항상 Bright Data 다.
    crawler_body_fetcher: str = Field(
        default="insane",
        description='본문 fetcher. "insane"=하이브리드 폴백, "brightdata"=Bright Data 강제',
    )
    # insane_concurrent_limit 은 domain/crawler/insane_fetcher.py 의 module-level
    # BoundedSemaphore 가 실제 소비(no-op 아님). 단일 IP 라 보수적 default 3.
    insane_concurrent_limit: int = Field(
        default=3, description="insane(curl_cffi) fetch 동시 호출 한도 (단일 IP 보수적)"
    )
    insane_timeout_seconds: int = Field(
        default=30, description="insane(curl_cffi) fetch 요청 타임아웃 (초)"
    )

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

    # SPEC-BATCH Phase 2 PR2 — cluster 재사용 대기 정책. primary 미완료 시 member 가
    # polling 으로 대기. 타임아웃 시 cluster 재사용 폴백 → 자체 분석.
    batch_cluster_primary_timeout_sec: int = Field(
        default=600, description="cluster member 가 primary 완료를 기다리는 최대 초"
    )
    batch_cluster_poll_interval_sec: float = Field(
        default=1.0, description="cluster member 의 primary 상태 polling 주기 (초)"
    )

    # SPEC-BATCH §12 Phase 5+ PR1 — cluster member 본문 차별화 검증.
    # cluster_dedupe ON 정책의 1페이지 노출 리스크 mitigation. member 가 primary 의
    # PatternCard 재사용해 본문 생성 후 단어 3-gram Jaccard 측정. 임계값 초과 시
    # 자동 needs_review (검수 큐에서 운영자가 차별화 보강).
    cluster_body_similarity_enabled: bool = Field(
        default=True,
        description="cluster member 본문 차별화 검증 ON/OFF. cluster_dedupe ON 일 때만 의미",
    )
    cluster_body_similarity_threshold: float = Field(
        default=0.7,
        description="단어 3-gram Jaccard 임계값. 이 이상이면 needs_review 강제 마킹",
    )

    # SPEC-BATCH Phase 4 PR1 — Slack 알림 (선택). webhook 미설정 시 모든 알림 noop.
    # 검수 큐가 1차 운영 도구이므로 개별 의료법 위반 알림은 별도 toggle 로 제어
    # (운영 노이즈 회피). 대량 처리 중 false 가 default.
    slack_webhook_url: str | None = Field(
        default=None,
        description="Slack incoming webhook URL — 미설정 시 모든 알림 noop",
    )
    slack_notify_compliance_violations: bool = Field(
        default=False,
        description="개별 의료법 위반 알림 ON/OFF (검수 큐 외 추가 알림이 필요할 때만 true)",
    )
    slack_review_queue_threshold: int = Field(
        default=0,
        description="검수 큐 누적 임계 (0 = 비활성). batch 의 needs_review 가 이 값 이상이면 1회 알림",
    )

    # SPEC-BATCH Phase 3 PR2 — overnight cron 시간대 게이트.
    # `scripts/run_batch.py --dispatch-overnight` 가 외부 cron (GitHub Actions /
    # Render cron) 에서 호출되며, 게이트 시간대가 아니면 noop (exit 0). 운영자가
    # `--overnight-batch-id` 로 명시 호출 시 게이트 우회.
    batch_overnight_hour_kst: int = Field(
        default=22, description="overnight dispatch 가 활성화되는 KST 시각 (0~23)"
    )
    batch_overnight_force: bool = Field(
        default=False,
        description="overnight 시간대 게이트 무시 (env 즉시 트리거 / 테스트용)",
    )

    # Phase J2 (2026-05-08) — Job 상태 Supabase 영속화. feature flag 로 단계 도입.
    # default false → 기존 in-memory 동작 그대로. PR2 에서 staging 활성화 후 1주
    # 모니터링하며 운영 전환. flag 가 false 면 schema/storage 가 있어도 write/read
    # 안 함 (모든 신규 경로 noop, in-memory 100% fallback).
    job_persistence_enabled: bool = Field(
        default=False,
        description="Supabase jobs 테이블에 작업 상태 write-through. false 면 기존 in-memory 만",
    )
    # heartbeat 갱신 주기. 짧을수록 false orphaned 가능성 ↓, DB write 횟수 ↑.
    # 30s 가 기본값 — 5분 grace 대비 충분히 짧고 분당 2회만 write.
    job_heartbeat_seconds: int = Field(
        default=30, description="running job 의 last_heartbeat 갱신 주기 (초)"
    )
    # last_heartbeat 가 이 시간 초과되면 sweep 이 orphaned 마킹.
    # PR4 첫 24h 는 900 (15분) 보수, 운영 데이터 누적 후 300 (5분) 단축 권장.
    job_orphaned_grace_seconds: int = Field(
        default=300,
        description="last_heartbeat 만료 grace (초). 이 시간 동안 갱신 없으면 orphaned",
    )
    # 5분 주기 sweep 으로 stale heartbeat 모두 orphaned 마킹. flag on 일 때만 시작.
    # 운영 부하 ↓ 위해 짧게 줄이지 않는다 — 본 파일의 grace 가 정확도, sweep 간격
    # 은 검출 지연. 운영자가 빠른 검출을 원하면 60s 까지 단축 가능.
    job_sweep_interval_seconds: int = Field(
        default=300,
        description="orphaned sweep 주기 (초). flag on 시 lifespan 에서 asyncio.create_task",
    )

    # ── Phase AP — 자동 발행 (2026-05-10) ─────────────────────
    # 자산 위험이 가장 높은 영역. 사고 방지 위해 default False 로 강제 opt-in.
    # 차용: seokcess-kk/auto-publishing@c64b5e7 (MIT, MoonbirdThinker).
    publishing_enabled: bool = Field(
        default=False,
        description="자동 발행 마스터 스위치. False 면 NaverBlogPublisher 인스턴스 생성 자체 거부",
    )
    naver_username: str | None = Field(
        default=None, description="네이버 ID — RSA 폴백 로그인용. CDP 우선이면 미설정 가능"
    )
    naver_password: str | None = Field(default=None, description="네이버 PW — RSA 폴백 로그인용")
    naver_chrome_profile: str | None = Field(
        default=None,
        description="CDP 로그인에 사용할 Chrome 프로필명 (예: 'Profile 2'). 5채널 시 채널별 오버라이드",
    )
    chrome_path: str | None = Field(
        default=None,
        description="chrome.exe 절대경로. 미설정 시 OS 기본 경로 자동 탐지",
    )
    # Phase AP-C 5채널 LRU 운영 — 동일 채널 반복 발행 방지
    min_publish_interval_minutes: int = Field(
        default=30,
        description="동일 채널 직전 발행에서 최소 대기 시간 (분). LRU 선택 시 가드",
    )
    block_medical_auto_publish: bool = Field(
        default=False,
        description="의료 카테고리 자동 발행 차단. True 시 의료 키워드는 수동 발행만 허용",
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
