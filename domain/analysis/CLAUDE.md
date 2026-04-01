# Analysis 도메인 규칙

## 파일 역할
- `model.py`: L1Analysis, L2Analysis, VisualAnalysis, PatternCard Pydantic 모델
- `structure_analyzer.py`: L1 구조 분석 (HTML 파싱, LLM 불필요)
- `copy_analyzer.py`: L2 카피 분석 (Claude API 기반)
- `visual_analyzer.py`: DOM 파싱 + VLM 인터페이스 (VLM은 추후 연결)
- `pattern_card.py`: L1+L2+비주얼 통합 → PatternCard 생성

## L1 vs L2 구분
- L1은 LLM을 호출하지 않는다. BeautifulSoup/lxml로 정량 데이터만 추출
- L2는 LLM이 필수. 포스트별 개별 분석 → N개 결과 집계
- L1과 L2는 병렬 실행 가능 (fan-out)

## 패턴 카드 원칙
- 뼈대(skeleton): 구조적 제약 — 변이 엔진이 범위 내에서만 변이
- 살(free): 자유 영역 — 프로필 기반으로 자유롭게 생성
- P25~P75 범위로 극단값 제거
- 5개 미만 포스트 분석 시 confidence: "low"
