# Crawler Domain

Bright Data SERP + Web Unlocker 기반 네이버 블로그 수집. SPEC.md §3 [1][2] 구현.

## 핵심 규칙

1. **모든 Bright Data 호출은 `brightdata_client.py` 경유** — 개별 파일에서 `requests.post()` 직접 호출 금지
2. **네이버 블로그만 필터** — `blog.naver.com` / `m.blog.naver.com` 외 URL 배제, 광고 섹션 제외, SERP 쿼리에 `&where=blog` 사용
3. **최소 7개 수집 성공 필수** — 미만이면 `InsufficientCollectionError` 발생, 파이프라인 종료
4. **재시도 2회** — URL당 exponential backoff (2s → 5s), 타임아웃 30초
5. **⚠️ iframe 재요청 여부는 착수 시 실측 후 확정** — Web Unlocker 1회 호출로 JS 렌더링 HTML이 오면 2단계 불필요. 실측 결과를 `tasks/lessons.md` 에 기록

## 파일 책임

- `brightdata_client.py` — 공통 HTTP 클라이언트, 인증, 타임아웃·재시도 로직
- `serp_collector.py` — SERP 쿼리 + 네이버 블로그 URL 필터 + 선착순 10개 선택
- `page_scraper.py` — Web Unlocker 호출 (iframe 처리는 실측 후 확정)
- `model.py` — `SerpResult`, `BlogPage`, `InsufficientCollectionError` 등 Pydantic 모델

## 금지

- Scrapling, Playwright, 기타 대체 크롤링 라이브러리 사용 금지 (Bright Data로 통일)
- 네이버 외 플랫폼(티스토리, 워드프레스 등) 크롤링 금지 (범위 밖)
- API 키 하드코딩 금지 (`config/.env` 단일 출처)
- `print()` 금지 (`logging` 사용)

## 참조

- @../../SPEC.md §3 [1][2]
- @../../.claude/skills/crawling/SKILL.md
