"""Blog channel 도메인 — 운영자가 보유한 네이버 블로그 채널 메타 (격리).

publications / keyword_batch_items 가 nullable FK 로 참조한다. 발행 자체는
운영자가 외부에서 수동 수행 (Selenium/네이버 API 사용 X) — 본 도메인은 단순
메타 + 추적용.
"""
