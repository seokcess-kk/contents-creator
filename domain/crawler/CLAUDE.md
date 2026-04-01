# Crawler 도메인 규칙

## 파일 역할
- `naver_search.py`: 네이버 검색 API 호출 (urllib, LLM 불필요)
- `blog_scraper.py`: Scrapling으로 블로그 본문 HTML 추출 (iframe 처리)
- `screenshot.py`: Playwright 풀페이지 스크린샷 (680px, async)
- `homepage_scraper.py`: 일반 웹페이지 크롤링 (프로필 도메인과 공유)
- `pipeline.py`: 전체 크롤링 파이프라인 통합
- `model.py`: Pydantic 데이터 모델

## 네이버 블로그 특화
- iframe 내부 본문: `div.se-main-container` (SE3) 또는 `div#postViewArea` (구버전)
- 모바일 URL `m.blog.naver.com` → `blog.naver.com`으로 변환
- 지도/구분선/인용구 블록 태그 보존

## 에러 처리
- 모든 외부 호출은 3회 재시도 + 지수 백오프
- 실패 시 해당 포스트 스킵, error 필드에 기록
- 비공개/삭제 포스트는 success=False로 처리
