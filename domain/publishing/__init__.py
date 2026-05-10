"""Publishing 도메인 — 네이버 블로그 자동 발행 (격리).

운영자가 보유한 BlogChannel 1개에 대해 RabbitWrite.naver API 로 SE 에디터
documentModel 을 POST 하여 글을 등록한다. 인증 / 본문 변환 / 발행 / 시도 로그
까지 격리된 단위로 캡슐화. 운영 가드는 application 레이어가 책임진다.

차용: seokcess-kk/auto-publishing@c64b5e7 (MIT, MoonbirdThinker)
- common/auth.py            → publishing/auth.py
- common/session.py         → publishing/session.py
- publishers/naver_blog.py  → publishing/naver_publisher.py + document_builder.py

Phase AP-A (PoC): 단일 블로그 + 평문 변환 + 1글 RabbitWrite 성공.
Phase AP-B: 풀 SE 변환 + 이미지 업로드.
Phase AP-C: 5채널 LRU + 검수 큐 자동 트리거.
"""
