# Publishing Domain

네이버 블로그 자동 발행. Phase AP 구현. 운영 위험이 가장 높은 도메인이라 가드가 두텁다.

## 차용 출처 (필수 준수)

- 원본: [seokcess-kk/auto-publishing](https://github.com/seokcess-kk/auto-publishing) `@c64b5e7`
- 라이센스: MIT (Copyright 2026 MoonbirdThinker)
- 차용 파일은 모듈 docstring 첫 줄에 `Adapted from seokcess-kk/auto-publishing@<sha>` 명시

## 책임 범위

- **포함**: 네이버 로그인(CDP/RSA), 세션 캐시, HTML→SE documentModel 변환, RabbitWrite POST, 발행 시도 로그
- **불포함**: 검수 큐 라우팅, 의료법 재검증, register_publication 호출, LRU 채널 선택 (모두 application 레이어)

## 🔴 운영 가드 (절대 위반 불가)

- `settings.publishing_enabled = False` 면 `NaverBlogPublisher.publish()` 즉시 `PublishingDisabledError` raise
- `dry_run=True` 시 RabbitWrite POST 호출 금지 (documentModel JSON 만 반환)
- 본 도메인은 `register_publication` / `compliance.checker` 직접 호출 금지 — application 레이어가 조율
- 모든 발행 시도는 `publishing_attempts` 테이블에 기록 (성공·실패 무관)

## 파일 책임

| 파일 | 책임 |
|---|---|
| `model.py` | `PublishRequest`, `PublishResult`, `PublishingError`, `PublishingDisabledError` Pydantic |
| `auth.py` | `naver_login_cdp` (1순위), `naver_login` RSA (폴백) |
| `session.py` | `SessionManager` — `.sessions/<channel>.pkl` 쿠키 영속 |
| `document_builder.py` | `build_document_model(html, title, *, full_se=False)` — PoC 평문, B 단계 풀 SE |
| `naver_publisher.py` | `NaverBlogPublisher.publish(req) -> PublishResult` — 로그인 + RabbitWrite |
| `storage.py` | `publishing_attempts` CRUD (Supabase) |

## SE documentModel 핵심 구조

```python
{
    "documentId": "",  # update 시 logNo
    "document": {
        "version": "2.8.0",
        "theme": "default",
        "language": "ko-KR",
        "id": "<uuid 26자>",
        "components": [
            {"@ctype": "documentTitle", "title": [...], "subTitle": None, ...},
            {"@ctype": "text", "value": [paragraph...], ...},
            {"@ctype": "table", "rows": [...], "columnCount": N, ...},
            # PoC 단계는 documentTitle + text 만 사용
        ],
        "di": {"dif": False, "dio": [...]},
    },
}
```

`@ctype` 필수, 모든 노드에 `id: SE-<uuid>` 필수, paragraph 은 `nodes: list[textNode]` 구조.

## RabbitWrite 응답 처리

- `isSuccess: false` → `PublishResult(success=False, message="<errorCode>: <errorMessage>")`. 재시도 금지 (네이버 차단 트리거 회피)
- `isSuccess: true` + `redirectUrl` 의 `logNo=(\d+)` → `PublishResult(success=True, url="https://blog.naver.com/{blog_id}/{log_no}", post_id=log_no)`
- `isSuccess: true` 인데 logNo 추출 실패 → `success=False` (응답 포맷 변경 가능성, 재발행 위험 회피)

## 금지

- `_rabbit_write` 자동 재시도 루프 (네이버는 동일 본문 중복 POST 를 abuse 로 분류)
- 하드코딩된 NAVER_USERNAME/PASSWORD — 반드시 `config.settings` 경유
- 외부 이미지 URL 을 SE `image` 컴포넌트에 직접 삽입 (네이버 업로드 API 우회 필요 — Phase AP-B 까지 미사용)
- application 레이어 import (역방향)
- print(), bare except, --no-verify

## 참조

- SPEC: 본 도메인은 SPEC 미정 (운영 안정 후 SPEC-PUBLISHING.md 작성 검토)
- Plan: `tasks/todo.md` 의 "Phase AP — 자동 발행" 섹션
- 원본: `seokcess-kk/auto-publishing/publishers/naver_blog.py`, `common/auth.py`, `common/session.py`
