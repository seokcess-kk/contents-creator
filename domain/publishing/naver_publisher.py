"""Naver 블로그 자동 발행 — RabbitWrite POST.

Adapted from seokcess-kk/auto-publishing@c64b5e7 (MIT) publishers/naver_blog.py.
원본의 멀티 도메인 documentModel 빌더(쿠팡/뉴스픽/일출일몰)를 제거하고 우리
document_builder 단일 호출로 단순화.

운영 가드: settings.publishing_enabled=False 면 publish() 가 즉시
PublishingDisabledError raise. dry_run=True 시 RabbitWrite POST 호출 금지.
"""

from __future__ import annotations

import json
import logging
import re

from config.settings import settings

from .auth import naver_login, naver_login_cdp
from .document_builder import build_document_model, build_population_params
from .model import PublishingDisabledError, PublishRequest, PublishResult
from .session import SessionManager

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_RABBIT_WRITE_URL = "https://blog.naver.com/RabbitWrite.naver"


class NaverBlogPublisher:
    """단일 채널 1개에 대해 RabbitWrite POST 1회.

    인스턴스 1개 = 채널 1개. session_mgr 의 .pkl 캐시는 채널별로 분리된다.
    재시도 루프 없음 — 네이버가 동일 본문 중복 POST 를 abuse 로 분류할 위험 회피.

    호출 패턴:
        publisher = NaverBlogPublisher(blog_id="myblog", username="...", password="...")
        result = publisher.publish(req, dry_run=False)
        if result.success:
            ranking_orchestrator.register_publication(url=result.url, ...)
    """

    def __init__(
        self,
        *,
        blog_id: str,
        username: str,
        password: str,
        chrome_profile: str | None = None,
        session_name: str | None = None,
    ) -> None:
        if not settings.publishing_enabled:
            raise PublishingDisabledError(
                "settings.publishing_enabled=False — config/.env 의 PUBLISHING_ENABLED=true 필요"
            )
        self.blog_id = blog_id
        self.username = username
        self.password = password
        self.chrome_profile = chrome_profile or settings.naver_chrome_profile
        # 채널별 .pkl — 5채널 운영 시 channel_id 또는 blog_id 로 분리
        self.session_mgr = SessionManager(session_name or f"naver_blog_{blog_id}")

    # ── 로그인 ──────────────────────────────────────────────

    def login(self) -> bool:
        """저장 세션 → CDP → RSA 순서. 모두 실패 시 False.

        반환 False 시 호출자가 LoginFailedError 처리. publish() 는 자동 호출.
        """
        if self.session_mgr.load() and self.session_mgr.has_login_cookie():
            logger.info("publisher.login.cache_hit blog_id=%s", self.blog_id)
            return True

        if naver_login_cdp(self.session_mgr.session, chrome_profile=self.chrome_profile):
            self.session_mgr.save()
            return True

        logger.warning("publisher.login.cdp_failed blog_id=%s — RSA 폴백", self.blog_id)
        if not (self.username and self.password):
            logger.error("publisher.login.no_credentials blog_id=%s", self.blog_id)
            return False
        if naver_login(self.session_mgr.session, self.username, self.password):
            self.session_mgr.save()
            return True

        logger.error("publisher.login.all_failed blog_id=%s", self.blog_id)
        return False

    # ── 발행 ────────────────────────────────────────────────

    def publish(self, req: PublishRequest, *, dry_run: bool = False) -> PublishResult:
        """RabbitWrite POST 1회. dry_run=True 면 documentModel 만 반환 (POST 없음).

        Acceptance:
            - settings.publishing_enabled=False → __init__ 에서 raise (여기 도달 X)
            - req.blog_id != self.blog_id → ValueError (안전망 — 채널 혼선 방지)
            - dry_run=True → success=True + url="" + message="dry_run"
            - login 실패 → success=False + message 에 사유
            - RabbitWrite isSuccess=false → success=False + errorCode/Message
            - logNo 추출 성공 → success=True + url="https://blog.naver.com/{blog_id}/{logNo}"
        """
        if req.blog_id != self.blog_id:
            raise ValueError(
                f"publisher.blog_id={self.blog_id!r} 와 req.blog_id={req.blog_id!r} 불일치"
            )

        document_model = build_document_model(
            title=req.title,
            content_html=req.content_html,
            full_se=req.full_se,
        )
        population_params = build_population_params(
            category_no=req.category_no,
            tags=req.tags,
        )

        if dry_run:
            logger.info(
                "publisher.dry_run blog_id=%s title=%r tags=%d",
                self.blog_id,
                req.title,
                len(req.tags),
            )
            # documentModel JSON 을 response_excerpt 에 일부 담아 사후 검증 가능
            preview = json.dumps(document_model, ensure_ascii=False)[:500]
            return PublishResult(
                success=True,
                url="",
                post_id="",
                message="dry_run",
                response_excerpt=preview,
            )

        if not self.login():
            return PublishResult(
                success=False,
                message="login_failed: CDP/RSA 모두 실패. .sessions/<name>.pkl 수동 갱신 필요",
            )

        return self._rabbit_write(document_model, population_params)

    # ── 내부 ────────────────────────────────────────────────

    def _rabbit_write(
        self,
        document_model: dict,
        population_params: dict,
    ) -> PublishResult:
        headers = {
            "authority": "blog.naver.com",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://blog.naver.com",
            "referer": f"https://blog.naver.com/{self.blog_id}/postwrite",
            "user-agent": _USER_AGENT,
        }
        data = {
            "blogId": self.blog_id,
            "documentModel": json.dumps(document_model, ensure_ascii=False),
            "populationParams": json.dumps(population_params, ensure_ascii=False),
            "productApiVersion": "v1",
        }

        try:
            resp = self.session_mgr.post(
                _RABBIT_WRITE_URL,
                headers=headers,
                data=data,
                timeout=30,
            )
        except Exception as exc:
            logger.error("publisher.post.exception blog_id=%s err=%s", self.blog_id, exc)
            return PublishResult(success=False, message=f"http_exception: {exc}")

        excerpt = (resp.text or "")[:500]

        if not resp.ok:
            logger.error(
                "publisher.post.http_failed blog_id=%s status=%s",
                self.blog_id,
                resp.status_code,
            )
            return PublishResult(
                success=False,
                message=f"HTTP {resp.status_code}",
                response_excerpt=excerpt,
            )

        try:
            payload = resp.json()
        except ValueError:
            logger.error("publisher.post.json_parse_failed blog_id=%s", self.blog_id)
            return PublishResult(
                success=False,
                message="json_parse_failed",
                response_excerpt=excerpt,
            )

        # isSuccess=false → 즉시 실패 (재시도 금지)
        if payload.get("isSuccess") is False:
            err = payload.get("result") or {}
            msg = (
                f"isSuccess=false code={err.get('errorCode', '')} msg={err.get('errorMessage', '')}"
            )
            logger.error("publisher.post.api_failed blog_id=%s %s", self.blog_id, msg)
            return PublishResult(success=False, message=msg, response_excerpt=excerpt)

        # logNo 추출 — redirectUrl 우선, 그 다음 raw text 정규식
        log_no = ""
        redirect_url = ((payload.get("result") or {}).get("redirectUrl")) or ""
        if redirect_url:
            m = re.search(r"logNo=(\d+)", redirect_url)
            if m:
                log_no = m.group(1)
        if not log_no:
            for pattern in (r'"logNo"\s*:\s*"?(\d+)', r"logNo=(\d+)"):
                m = re.search(pattern, resp.text)
                if m:
                    log_no = m.group(1)
                    break

        if not log_no:
            logger.warning(
                "publisher.post.no_log_no blog_id=%s — isSuccess=true 인데 logNo 추출 실패",
                self.blog_id,
            )
            return PublishResult(
                success=False,
                message="no_log_no (isSuccess=true 이나 redirectUrl 에서 logNo 추출 실패)",
                response_excerpt=excerpt,
            )

        post_url = f"https://blog.naver.com/{self.blog_id}/{log_no}"
        logger.info("publisher.post.success blog_id=%s url=%s", self.blog_id, post_url)
        return PublishResult(
            success=True,
            url=post_url,
            post_id=log_no,
            message="ok",
            response_excerpt=excerpt,
        )


__all__ = ["NaverBlogPublisher"]
