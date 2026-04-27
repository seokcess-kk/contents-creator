"""네이버 블로그 URL 정규화 + 매칭 — ranking 도메인 단일 출처.

🔴 중요 — 정규식 의도적 복제:
`BLOG_POST_URL_RE` 는 `domain/crawler/serp_collector.py` 와 동일하다.
도메인 격리(ranking → crawler 직접 import 금지) 원칙을 지키기 위한
의도적 복제이며, serp_collector 가 변경되면 본 파일도 동시 갱신해야 한다.
tasks/lessons.md 참조.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# serp_collector.BLOG_POST_URL_RE 와 동일 패턴 (의도적 복제)
BLOG_POST_URL_RE = re.compile(r"^https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}$")

_USERID_POSTID_RE = re.compile(r"^/([a-zA-Z0-9_-]+)/(\d{9,})/?$")


def normalize_blog_url(raw: str) -> str | None:
    """네이버 블로그 포스트 URL 정규화.

    - 스킴 없으면 https:// 보정
    - 호스트를 m.blog.naver.com 으로 통일 (모바일 본문 단일 호출 정책)
    - 트레일링 슬래시·쿼리스트링 제거
    - 형식 위반 시 None
    """
    if not raw:
        return None
    candidate = raw.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = "https://" + candidate

    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    if host not in ("blog.naver.com", "m.blog.naver.com"):
        return None

    match = _USERID_POSTID_RE.match(parsed.path)
    if match is None:
        return None

    userid, postid = match.group(1), match.group(2)
    normalized = f"https://m.blog.naver.com/{userid}/{postid}"
    if not BLOG_POST_URL_RE.match(normalized):
        return None
    return normalized


def urls_match(a: str, b: str) -> bool:
    """두 네이버 블로그 URL 이 같은 포스트를 가리키는가."""
    na = normalize_blog_url(a)
    nb = normalize_blog_url(b)
    if na is None or nb is None:
        return False
    return na == nb


def normalize_any_url(raw: str) -> str | None:
    """범용 URL 정규화 — 카페·인플루언서·외부 사이트도 허용.

    네이버 블로그면 모바일 도메인으로 통일하고, 그 외에는 host lowercase +
    path 트레일링 슬래시 제거 + 쿼리·프래그먼트 제거 후 https:// 형태로 반환.
    형식 위반(scheme/host 추출 실패) 시 None.
    """
    if not raw:
        return None
    blog = normalize_blog_url(raw)
    if blog is not None:
        return blog
    candidate = raw.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    if not host:
        return None
    path = parsed.path.rstrip("/")
    return f"https://{host}{path}"


def urls_match_any(a: str, b: str) -> bool:
    """두 URL 이 같은 콘텐츠를 가리키는가 (네이버 블로그 외 일반 URL 도 허용)."""
    na = normalize_any_url(a)
    nb = normalize_any_url(b)
    if na is None or nb is None:
        return False
    return na == nb
