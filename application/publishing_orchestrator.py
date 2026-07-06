"""자동 발행 오케스트레이션 — 검수 통과 콘텐츠 → 네이버 발행 → 순위 등록.

Phase AP-A (PoC): 단일 채널 + 평문 변환 + 1글 RabbitWrite.
- output/{slug}/{ts}/content/seo-content.html 을 읽어
- BlogChannel 1개 지정 → NaverBlogPublisher.publish() 호출
- publishing_attempts 영속 → 성공 시 ranking_orchestrator.register_publication

운영 가드:
- settings.publishing_enabled=False 면 NaverBlogPublisher.__init__ 에서 raise
- dry_run=True 시 RabbitWrite POST 호출 없이 documentModel 만 반환
- 의료법 재검증은 Phase AP-B 에서 자동화. PoC 는 운영자가 검수 통과시킨 콘텐츠
  만 발행한다는 신뢰 가정 (block_medical_auto_publish=true 시 한의원/의원 키워드 거부)

Phase AP-C 진입 시 추가될 함수: auto_publish_approved_items(batch_id) — 검수 큐
approve 시 자동 트리거. LRU 채널 선택 + min_publish_interval 가드.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from application import ranking_orchestrator
from config.settings import settings
from domain.blog_channel.model import BlogChannel
from domain.publishing import storage as publishing_storage
from domain.publishing.model import (
    PublishingAttempt,
    PublishingDisabledError,
    PublishingError,
    PublishRequest,
    PublishResult,
)
from domain.publishing.naver_publisher import NaverBlogPublisher

logger = logging.getLogger(__name__)

# 의료 키워드 차단 — block_medical_auto_publish=true 시 검사
_MEDICAL_KEYWORDS = (
    "한의원",
    "의원",
    "병원",
    "의료",
    "치과",
    "피부과",
    "정형외과",
    "성형외과",
    "내과",
    "안과",
    "산부인과",
    "비뇨기과",
    "소아과",
    "한약",
    "시술",
    "수술",
    "치료",
    "진료",
)


def publish_from_output_dir(
    *,
    output_dir: Path,
    channel: BlogChannel,
    keyword: str,
    job_id: str | None = None,
    tags: list[str] | None = None,
    category_no: int = 0,
    dry_run: bool = False,
    register_after_publish: bool = True,
) -> PublishResult:
    """`output/{slug}/{ts}/` 1개 → 채널 1개 발행.

    호출 흐름:
        1. output_dir/content/seo-content.html 읽기 (없으면 PublishingError)
        2. title 추출 — outline.json 의 title 우선, fallback: <h1> 또는 첫 paragraph
        3. block_medical_auto_publish 가드 — 의료 키워드 + dry_run=False 조합 시 거부
        4. NaverBlogPublisher.publish(req, dry_run)
        5. publishing_attempts 영속 (best-effort, 실패해도 본 흐름 유지)
        6. dry_run=False + success + register_after_publish → ranking_orchestrator.register_publication

    Args:
        output_dir: `output/{slug}/{ts}/` (또는 `latest` symlink). content/seo-content.html 존재 필수
        channel:    BlogChannel — name + blog_id 사용. is_default 무관
        keyword:    추적용 키워드 (publishing_attempts.keyword 컬럼)
        job_id:     원본 job_id (선택)
        tags:       발행 태그. 미지정 시 outline.json 의 suggested_tags 사용
        category_no: 네이버 카테고리 ID. 0 = 기본
        dry_run:    True 면 documentModel JSON 만 build_dryrun.json 으로 저장 + POST 없음
        register_after_publish: True 시 발행 성공 → register_publication 자동 호출

    Returns:
        PublishResult — application 레이어가 사용자/CLI 에 그대로 노출
    """
    if not settings.publishing_enabled:
        raise PublishingDisabledError(
            "settings.publishing_enabled=False — config/.env 의 PUBLISHING_ENABLED=true 필요"
        )

    html_path = output_dir / "content" / "seo-content.html"
    if not html_path.exists():
        raise PublishingError(f"콘텐츠 HTML 미존재: {html_path}")

    content_html = html_path.read_text(encoding="utf-8")

    title = _extract_title(output_dir, content_html, keyword)
    final_tags = tags if tags is not None else _extract_tags(output_dir)

    slug = (
        output_dir.parent.name
        if output_dir.name and output_dir.name[0].isdigit()
        else output_dir.name
    )

    # 의료 키워드 자동 발행 차단 (dry_run 은 통과 — 사전 검증 목적)
    if (
        settings.block_medical_auto_publish
        and not dry_run
        and any(mk in keyword for mk in _MEDICAL_KEYWORDS)
    ):
        msg = (
            f"의료 키워드 자동 발행 차단: {keyword!r} — "
            "BLOCK_MEDICAL_AUTO_PUBLISH=true 운영 정책. 수동 발행만 허용"
        )
        logger.warning("publishing_orchestrator.medical_blocked keyword=%s", keyword)
        attempt = PublishingAttempt(
            channel_id=channel.id,
            keyword=keyword,
            slug=slug,
            job_id=job_id,
            status="failed",
            message=msg,
        )
        publishing_storage.insert_attempt(attempt)
        return PublishResult(success=False, message=msg)

    req = PublishRequest(
        blog_id=channel.blog_id,
        title=title,
        content_html=content_html,
        tags=final_tags,
        category_no=category_no,
        full_se=False,  # PoC 평문 고정
        keyword=keyword,
        slug=slug,
        job_id=job_id,
        channel_id=channel.id,
    )

    publisher = NaverBlogPublisher(
        blog_id=channel.blog_id,
        username=settings.naver_username or "",
        password=settings.naver_password or "",
        chrome_profile=settings.naver_chrome_profile,
        # 채널별 .pkl 분리 — 5채널 운영 시 각자 독립 세션
        session_name=f"naver_blog_{channel.blog_id}",
    )

    result = publisher.publish(req, dry_run=dry_run)

    # dry_run 결과는 documentModel JSON 을 파일로 보존 — 사후 검증
    if dry_run:
        # documentModel 본체를 저장해 사후 검증을 가능하게 한다 (PublishResult.response_excerpt
        # 는 500자만 발췌하므로 dry-run 만으로 SE 변환 정합성을 따지기 어렵다).
        from domain.publishing.document_builder import (
            build_document_model,
            build_population_params,
        )

        full_document = build_document_model(title=title, content_html=content_html, full_se=False)
        full_population = build_population_params(category_no=category_no, tags=final_tags)
        dryrun_path = output_dir / "_publish_dryrun.json"
        dryrun_path.write_text(
            json.dumps(
                {
                    "channel": {"id": channel.id, "name": channel.name, "blog_id": channel.blog_id},
                    "title": title,
                    "tags": final_tags,
                    "category_no": category_no,
                    "document_model": full_document,
                    "population_params": full_population,
                    "result": result.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("publishing_orchestrator.dry_run_saved path=%s", dryrun_path)

    # 발행 시도 영속 (best-effort)
    attempt_status = "dry_run" if dry_run else ("success" if result.success else "failed")
    attempt = PublishingAttempt(
        channel_id=channel.id,
        keyword=keyword,
        slug=slug,
        job_id=job_id,
        status=attempt_status,
        post_url=result.url or None,
        post_id=result.post_id or None,
        message=result.message,
        response_excerpt=result.response_excerpt,
        attempted_at=result.attempted_at,
    )
    publishing_storage.insert_attempt(attempt)

    # 성공 + dry_run 아님 + register_after_publish → 순위 추적 진입
    if result.success and not dry_run and register_after_publish and result.url:
        try:
            publication = ranking_orchestrator.register_publication(
                keyword=keyword,
                url=result.url,
                slug=slug,
                job_id=job_id,
                published_at=result.attempted_at or datetime.now(),
                blog_channel_id=channel.id,
            )
            logger.info(
                "publishing_orchestrator.registered keyword=%s url=%s publication_id=%s",
                keyword,
                result.url,
                publication.id,
            )
        except Exception as exc:
            # register 실패는 발행 자체를 실패로 보지 않는다 — URL 은 수동 등록 가능
            logger.warning(
                "publishing_orchestrator.register_failed url=%s err=%s",
                result.url,
                exc,
            )

    return result


# ── 헬퍼 ──────────────────────────────────────────────────────


def _extract_title(output_dir: Path, content_html: str, keyword_fallback: str) -> str:
    """outline.json 의 title → seo-content.html 의 첫 heading → keyword 폴백."""
    outline_path = output_dir / "content" / "outline.json"
    if outline_path.exists():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
            title = outline.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        except Exception as exc:
            logger.warning("publishing_orchestrator.outline_parse_failed err=%s", exc)

    # H1 또는 첫 H2
    m = re.search(r"<h[12][^>]*>(.*?)</h[12]>", content_html, re.IGNORECASE | re.DOTALL)
    if m:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            return text

    return keyword_fallback or "제목 미지정"


def _extract_tags(output_dir: Path) -> list[str]:
    """outline.json 의 suggested_tags 추출. 미존재 시 빈 리스트."""
    outline_path = output_dir / "content" / "outline.json"
    if not outline_path.exists():
        return []
    try:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
        tags = outline.get("suggested_tags") or []
        return [str(t).strip() for t in tags if isinstance(t, str) and t.strip()]
    except Exception as exc:
        logger.warning("publishing_orchestrator.tags_parse_failed err=%s", exc)
        return []


__all__ = ["publish_from_output_dir"]
