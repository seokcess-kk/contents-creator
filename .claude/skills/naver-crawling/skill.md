---
name: naver-crawling
description: "네이버 블로그 상위 노출 콘텐츠를 크롤링하는 스킬. 네이버 검색 API로 키워드 상위 N개 URL을 수집하고, Scrapling(StealthyFetcher)으로 블로그 본문 HTML을 추출하며, Playwright로 풀페이지 스크린샷을 캡처한다. '크롤링', '수집', '상위글 가져와', '네이버 검색', '블로그 스크래핑' 요청 시 반드시 이 스킬을 사용할 것."
---

# 네이버 블로그 크롤링

## 실행 순서

1. **네이버 검색 API 호출** → 키워드 상위 N개 블로그 URL 목록 확보
2. **블로그 본문 수집** → Scrapling(StealthyFetcher)으로 각 URL의 HTML 추출
3. **스크린샷 캡처** → Playwright로 680px 뷰포트 풀페이지 스크린샷
4. **메타데이터 저장** → URL, 제목, 작성일, 수집 상태를 metadata.json에 기록

## 네이버 블로그 특화 처리

네이버 블로그는 iframe 구조를 사용한다. 본문 추출 시:
- `mainFrame` 내 `div.se-main-container` (스마트에디터 3.0) 또는 `div#postViewArea` (구버전) 탐색
- 네이버 지도 embed, 구분선(`<hr>`), 인용구 블록(`blockquote.se-quote`) 태그 보존
- 이미지는 `data-lazy-src` 또는 `src` 속성에서 원본 URL 추출

## Scrapling 설정

```python
from scrapling import StealthyFetcher

fetcher = StealthyFetcher()
# 네이버 블로그 접근 시 StealthyFetcher의 브라우저 핑거프린트 자동 관리 활용
# timeout: 15초, 재시도: 3회, 재시도 간격: 2초
```

## Playwright 스크린샷 설정

```python
# 뷰포트: 680px (네이버 블로그 모바일 기준)
# full_page=True
# timeout: 30초
# 이미지 로딩 대기: networkidle
```

## 출력 경로 규약

```
_workspace/01_crawl/
├── metadata.json
├── posts/
│   ├── {순번:02d}_raw.html
│   └── {순번:02d}_screenshot.png
└── errors.log
```

## 에러 처리

- 비공개/삭제 포스트 → 스킵, errors.log 기록
- 네이버 API 요청 한도 초과 → 대기 후 재시도
- SSL/네트워크 에러 → 3회 재시도, 실패 시 스킵
