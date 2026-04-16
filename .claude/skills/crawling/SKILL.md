---
name: crawling
description: Bright Data Web Unlocker 단일 zone 으로 네이버 블로그 상위 노출 글을 크롤링한다. 검색 결과 페이지와 본문 HTML 을 모두 Web Unlocker 로 fetch 한 뒤 BeautifulSoup 으로 파싱한다. 재시도 2회, 최소 7개 수집. 'Bright Data', 'SERP 수집', '네이버 블로그 크롤링', '본문 수집', '상위글 가져와' 요청 시 반드시 이 스킬을 사용할 것.
---

# Crawling Skill — Bright Data Web Unlocker

Bright Data Web Unlocker 단일 zone 으로 네이버 블로그 상위 노출 글을 수집한다. SPEC-SEO-TEXT.md §3 [1][2]를 구현한다.

**주**: Bright Data SERP API 는 Naver 전용 파서를 제공하지 않으므로(Google/Bing/Yandex/Baidu 만) 사용하지 않는다. Web Unlocker 가 범용 fetcher 이므로 검색 결과 페이지도 정상 fetch 되며, BeautifulSoup 으로 블로그 URL 을 직접 파싱한다.

## 책임 범위

- **포함**: 네이버 검색 → 블로그 URL 필터 → 본문 HTML 수집 → 저장
- **불포함**: HTML 파싱·분석(analysis 스킬), 스크린샷·VLM(추후 단계), 네이버 외 플랫폼

## 환경 변수 (config/.env)

```
BRIGHT_DATA_API_KEY=...
BRIGHT_DATA_WEB_UNLOCKER_ZONE=...   # SERP 수집 + 본문 수집 공용
```

모든 Bright Data 호출은 `domain/crawler/brightdata_client.py`의 공통 클라이언트를 경유한다. 개별 파일에서 `requests.post()`를 직접 호출하지 않는다.

## [1] SERP 수집 (serp_collector.py)

### 수집 정책 — 통합검색 우선 + 블로그 탭 보충

제품 의도는 **통합검색 상위 노출 블로그** 분석. 항상 `where=blog` 통합검색부터 시도하고, 표본이 부족하면 `ssc=tab.blog.all` 블로그 탭에서 최대 `BLOG_TAB_BOOST_LIMIT=5개` 만 보충한다. 실측 근거는 lessons.md C2.

1. **Step 1 — 통합검색** (`build_integrated_serp_url`):
   `search.naver.com/search.naver?query={kw}&where=blog`. 네이버 신버전 UI 는 통합검색 블로그 섹션에 6~7개만 초기 렌더한다 (`start` 파라미터 무시). 있는 만큼 수집.

2. **Step 2 — 블로그 탭 보충** (`build_blog_tab_serp_url`):
   통합검색 합계 < `MAX_RESULTS(10)` 이면 `search.naver.com/search.naver?ssc=tab.blog.all&query={kw}&start=1` fetch. 한 페이지에 40개 이상 서버 렌더링되므로 중복 제거 후 남은 슬롯 채움. **단, 블로그 탭 보충은 최대 5개**.

3. **Step 3 — 검증**: 합계 < `MIN_COLLECTED_PAGES(7)` → `InsufficientCollectionError`.

### 파서 규칙 (양 트랙 공통)
- **포스트 URL 은 `a[href]` 뿐 아니라 `*[data-url]` 속성에도 들어 있다** (네이버 신버전 UI `<button data-url="...">`). 파서는 둘 다 순회
- `blog.naver.com` / `m.blog.naver.com` 외 배제, `/clip/` (동영상 클립) 배제, 유저 홈 배제 (정규식 `[a-zA-Z0-9_-]+/\d{9,}`)
- 광고 섹션(`.sp_power_ad`, `#power_ad_container` 등) 제외
- 통합검색 결과의 원 순위는 rank 1~N 에 보존되고 블로그 탭 보충분이 뒤에 이어짐
- 각 `SerpResult` 에 `source: "integrated" | "blog_tab"` 필드로 출처 기록 — 패턴 카드까지 전파

### 출력 형식
```json
{
  "keyword": "강남 다이어트 한의원",
  "collected_at": "2026-04-15T20:00:00+09:00",
  "results": [
    {"rank": 1, "url": "https://blog.naver.com/...", "title": "...", "snippet": "..."},
    {"rank": 2, "url": "...", "title": "...", "snippet": "..."}
  ]
}
```

저장: `output/{slug}/{timestamp}/analysis/serp-results.json`

## [2] 본문 수집 (page_scraper.py)

### 재시도 정책
- URL당 최대 **2회 재시도** (총 3회 시도)
- Exponential backoff: 2초 → 5초
- 타임아웃: URL당 30초
- 2회 재시도 후에도 실패한 URL은 스킵 (예외 발생 안 함)

### 네이버 블로그 iframe 처리 (2026-04-15 실측 완료 ✅)

**확정 방침: 모든 블로그 URL 을 `m.blog.naver.com` 으로 정규화한 뒤 Web Unlocker 1회 호출.**

데스크톱 `blog.naver.com/{id}/{no}` 은 Web Unlocker 를 거쳐도 iframe 껍데기(3KB)만 반환된다. 반면 `m.blog.naver.com/{id}/{no}` 은 iframe 없이 본문이 직접 렌더되어 130KB 의 full HTML 이 단일 호출로 온다 (`se-main-container`, `se_component`, `post_ct`, `__se_module_data` 컨테이너 모두 포함).

**`page_scraper.py` 구현:**
```python
def normalize_to_mobile(url: str) -> str:
    # blog.naver.com/X/Y -> m.blog.naver.com/X/Y
    return re.sub(r"^https?://blog\.naver\.com/", "https://m.blog.naver.com/", url)

def fetch_blog_content(url: str) -> str:
    mobile_url = normalize_to_mobile(url)
    html = brightdata_client.web_unlocker_fetch(mobile_url, zone=...)
    return html  # 단일 호출 종료
```

mainFrame src 추출·재요청 로직은 불필요. 상세 실측 데이터: `tasks/lessons.md` C1 섹션.

**URL 필터 정규식**: `https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}` — `/clip/` (동영상), 유저 홈페이지 (`/{id}` 만) 배제.

### 최종 성공 수 확인
모든 URL 처리 후 성공 수가 **7개 미만**이면 `InsufficientCollectionError`. 7개 이상이면 파이프라인 진행.

### 출력 저장
- HTML 원본: `output/{slug}/{timestamp}/analysis/pages/{idx}.html`
- 메타: `output/{slug}/{timestamp}/analysis/pages/index.json`
  ```json
  {
    "successful": [{"idx": 0, "url": "...", "rank": 1, "path": "pages/0.html"}],
    "failed": [{"idx": 7, "url": "...", "rank": 8, "reason": "timeout"}]
  }
  ```

## 공통 클라이언트 (brightdata_client.py)

```python
class BrightDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.brightdata.com/request"

    def serp_search(self, query: str, where: str = "blog") -> str: ...
    def web_unlocker_fetch(self, url: str, zone: str) -> str: ...
```

모든 HTTP 호출은 `tenacity` 또는 수동 재시도 로직 + 명시적 타임아웃. 로깅은 `logging` 모듈, `print()` 금지.

## 테스트 체크리스트

- [ ] SERP API가 네이버 블로그 URL만 반환하는지
- [ ] 수집 수가 7개 미만일 때 명시적 에러가 발생하는지
- [ ] iframe URL 추출이 정상 동작하는지
- [ ] 재시도 2회 정책이 실제로 동작하는지 (mock으로 테스트)
- [ ] 저장 경로 구조가 SPEC-SEO-TEXT.md와 일치하는지

## 금지 사항

- `requests.get/post` 직접 호출 금지. `BrightDataClient` 경유
- `.env` 외부에서 API 키 하드코딩 금지
- 네이버 이외 플랫폼(티스토리·워드프레스) 크롤링 시도 금지 (현재 범위 밖)
- Scrapling·Playwright 같은 대안 라이브러리 사용 금지 (Bright Data로 통일)
