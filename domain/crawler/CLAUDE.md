# Crawler Domain

Bright Data SERP + Web Unlocker 기반 네이버 블로그 수집. SPEC-SEO-TEXT.md §3 [1][2] 구현.

## 핵심 규칙

1. **모든 Bright Data 호출은 `brightdata_client.py` 경유** — 개별 파일에서 `requests.post()` 직접 호출 금지. **본문([2]) 수집은 `HtmlFetcher` 추상화(`fetcher.py`) 경유** — 기본 insane(curl-only, cost=0) 우선 + Bright Data 폴백(`fallback_fetcher.py`). SERP·keyword_difficulty·ranking 은 여전히 Bright Data 단독
2. **네이버 블로그만 필터** — `blog.naver.com` / `m.blog.naver.com` 외 URL 배제, 광고 섹션 제외, SERP 쿼리에 `&where=blog` 사용
3. **최소 5개 수집 성공 필수** — 미만이면 `InsufficientCollectionError` 발생, 파이프라인 종료
4. **재시도 2회** — URL당 exponential backoff (2s → 5s), 타임아웃 30초
5. **⚠️ iframe 재요청 여부는 착수 시 실측 후 확정** — Web Unlocker 1회 호출로 JS 렌더링 HTML이 오면 2단계 불필요. 실측 결과를 `tasks/lessons.md` 에 기록

## 파일 책임

- `fetcher.py` — `HtmlFetcher` Protocol (fetch/close/`__enter__`/`__exit__` 4종). Bright Data·insane 공통 fetch 계약. 성공 판정 = `FetchResult.ok`, 실패 = `BrightDataError` 계열
- `brightdata_client.py` — 공통 HTTP 클라이언트, 인증, 타임아웃·재시도 로직. SERP + 본문 폴백 공용
- `insane_fetcher.py` — `vendor/insane_search`(curl-only, v0.9.1) 어댑터. 본문 1차 수집(cost=0), 실패 시 `InsaneFetchError`(BrightDataTransientError 하위)로 폴백 유도
- `fallback_fetcher.py` — primary(insane) → fallback(Bright Data) 하이브리드 합성. 폴백 시 `record_usage` 미호출(이중집계 차단)
- `serp_collector.py` — SERP 쿼리 + 네이버 블로그 URL 필터 + 선착순 10개 선택 (Bright Data 유지)
- `page_scraper.py` — 본문 HTML 수집. `HtmlFetcher` 를 받아 fetch (라우팅은 application `_build_body_fetcher()`)
- `model.py` — `SerpResult`, `BlogPage`, `InsufficientCollectionError` 등 Pydantic 모델

## 금지

- 임의 대체 크롤링 라이브러리 추가 금지 — 본문 수집은 **승인된 `vendor/insane_search`(curl-only, v0.9.1) 우선 + Bright Data 폴백** 하이브리드, SERP/ranking/keyword_difficulty 는 Bright Data. 이 둘 외의 라이브러리(Scrapling, Playwright 등, insane 의 Playwright Phase 포함) 도입은 여전히 금지
- 네이버 외 플랫폼(티스토리, 워드프레스 등) 크롤링 금지 (범위 밖)
- API 키 하드코딩 금지 (`config/.env` 단일 출처)
- `print()` 금지 (`logging` 사용)

## 참조

- SPEC-SEO-TEXT.md §3 [1][2]
- .claude/skills/crawling/SKILL.md
