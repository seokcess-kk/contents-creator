"""최소 documentModel 로 RabbitWrite 시도 — invalid parameter 의 원인이
components 안에 있는지(긴 본문 특정 컴포넌트), 다른 필드(editorSource 등)에
있는지 1회로 판가름.

usage:
    PUBLISHING_ENABLED=true python scripts/_debug_publish_minimal.py \\
        --channel-id b930187f-413c-496c-8ef7-13c3765b2322
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from domain.blog_channel import storage as channel_storage
from domain.publishing.model import PublishRequest
from domain.publishing.naver_publisher import NaverBlogPublisher


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--channel-id", required=True)
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    channel = channel_storage.get_channel(args.channel_id)
    if channel is None:
        print(f"channel not found: {args.channel_id}")
        return 2

    publisher = NaverBlogPublisher(
        blog_id=channel.blog_id,
        username="",
        password="",
        session_name=f"naver_blog_{channel.blog_id}",
    )

    req = PublishRequest(
        blog_id=channel.blog_id,
        title="테스트",
        content_html="<html><body><p>테스트</p></body></html>",
        tags=[],
        category_no=0,
        full_se=False,
        keyword="_debug",
        slug="_debug",
        channel_id=channel.id,
    )

    result = publisher.publish(req, dry_run=False)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
