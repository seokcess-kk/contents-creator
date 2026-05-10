"""Publishing 도메인 Pydantic 모델."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PublishRequest(BaseModel):
    """RabbitWrite POST 1건 요청.

    title/content_html/blog_id 는 필수. category_no=0 이면 미지정 (네이버 기본 카테고리).
    full_se=False (default) 는 Phase AP-A 평문 변환. True 는 Phase AP-B 풀 SE 변환.
    """

    blog_id: str = Field(min_length=1, description="네이버 블로그 식별자 — URL 의 마지막 segment")
    title: str = Field(min_length=1, max_length=200)
    content_html: str = Field(
        min_length=1, description="원고 HTML — naver-output.html 또는 그 변형"
    )
    tags: list[str] = Field(default_factory=list)
    category_no: int = 0
    full_se: bool = False  # Phase AP-A 동안 항상 False
    # 발행 직전 의료법 재검증 결과 추적용 — application 레이어가 채워서 전달
    compliance_revalidated: bool = False
    # 식별자 — 발행 시도 로그가 어느 콘텐츠인지 역추적
    keyword: str | None = None
    slug: str | None = None
    job_id: str | None = None
    channel_id: str | None = None  # blog_channels.id (FK)


class PublishResult(BaseModel):
    """RabbitWrite 응답 정규화.

    success=True: url + post_id 보장.
    success=False: message 에 사유 (errorCode/HTTP/예외).
    """

    success: bool
    url: str = ""
    post_id: str = ""
    message: str = ""
    # 운영 분석용 — application 레이어가 publishing_attempts 에 그대로 기록
    response_excerpt: str = Field(default="", max_length=500)
    attempted_at: datetime = Field(default_factory=datetime.now)


class PublishingAttempt(BaseModel):
    """publishing_attempts 1행. 모든 발행 시도(성공·실패)를 영속 기록."""

    id: str | None = None
    channel_id: str | None = None
    keyword: str | None = None
    slug: str | None = None
    job_id: str | None = None
    status: Literal["success", "failed", "dry_run"]
    post_url: str | None = None
    post_id: str | None = None
    message: str = ""
    response_excerpt: str = ""
    attempted_at: datetime | None = None


class PublishingError(Exception):
    """publishing 도메인 일반 에러. application 레이어가 catch."""


class PublishingDisabledError(PublishingError):
    """settings.publishing_enabled=False 일 때 publish() 호출 차단.

    운영 가드 — 사고 방지용 강제 raise. application 레이어에서 catch 하지 않고
    그대로 사용자에게 전달 (silent fallback 금지).
    """


class LoginFailedError(PublishingError):
    """CDP / RSA 모두 실패. 사용자가 수동 로그인 후 .sessions/<channel>.pkl 갱신 필요."""


__all__ = [
    "LoginFailedError",
    "PublishRequest",
    "PublishResult",
    "PublishingAttempt",
    "PublishingDisabledError",
    "PublishingError",
]
