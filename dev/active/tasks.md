# 작업 추적 — Contents Creator

> 최종 갱신: 2026-03-31

## Phase 0: 인프라 부트스트랩 ✅

- [x] SPEC.md 작성
- [x] CLAUDE.md 작성
- [x] 하네스 구성 (에이전트 + 스킬 + 오케스트레이터)
- [x] 하네스 리뷰 및 보완
- [x] Supabase 스키마 설계 (`config/supabase_schema.sql`)
- [x] dev/active/ 3대 문서 초기화

## Phase 1: MVP 핵심 파이프라인 ⬜

### 1-0. 프로젝트 초기 설정
- [ ] Python 프로젝트 초기화 (pyproject.toml, 의존성)
- [ ] Supabase 프로젝트 생성 + 스키마 배포
- [ ] .env 설정 (API 키)
- [ ] Git 초기화 + .gitignore

### 1-1. 크롤러 도메인
- [ ] 네이버 검색 API 연동 (상위 N개 URL 수집)
- [ ] Scrapling 블로그 본문 스크래핑 (iframe 처리)
- [ ] Playwright 스크린샷 캡처
- [ ] metadata.json 출력 + 에러 로깅
- [ ] 테스트 작성

### 1-2. 분석 도메인
- [ ] L1 구조 분석 (HTML 파싱)
- [ ] L2 카피 분석 (LLM 연동)
- [ ] 비주얼 분석 — DOM 파싱
- [ ] 비주얼 분석 — VLM 연동
- [ ] 패턴 카드 생성 (통합 + JSON 출력)
- [ ] 테스트 작성

### 1-3. 프로필 도메인
- [ ] 홈페이지/블로그 크롤링 (프로필 추출용)
- [ ] LLM 기반 프로필 자동 추출
- [ ] 사용자 리뷰 플로우
- [ ] Supabase CRUD
- [ ] 테스트 작성

### 1-4. 의료법 검증 도메인
- [ ] 금지 표현 규칙 엔진 (정규식 매칭)
- [ ] LLM 문맥 판단 검증
- [ ] 자동 수정 + 재검증 루프
- [ ] compliance_report.json 출력
- [ ] 테스트 작성

### 1-5. 생성 도메인
- [ ] 5개 층위 변이 엔진
- [ ] SEO 텍스트 생성 (LLM)
- [ ] 의료법 1차 방어 (프롬프트 주입)
- [ ] 디자인 카드 HTML 생성
- [ ] AI 이미지 프롬프트 생성
- [ ] 변이 조합 사용자 승인 플로우
- [ ] 테스트 작성

### 1-6. 조합 도메인
- [ ] HTML → PNG 렌더링 (Playwright)
- [ ] 최종 HTML 조합
- [ ] 네이버 에디터 최적화 포맷
- [ ] Disclaimer 자동 삽입
- [ ] 테스트 작성

### 1-7. 통합
- [ ] 전체 파이프라인 CLI (scripts/run_pipeline.py)
- [ ] 단독 실행 CLI (analyze.py, generate.py, validate.py)
- [ ] 통합 테스트 (정상 흐름 + 에러 흐름)

---

## 교훈 기록

`tasks/lessons.md`로 분리. 사용자 교정 시마다 갱신.
