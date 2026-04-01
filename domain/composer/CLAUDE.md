# Composer 도메인 규칙

## 파일 역할
- `model.py`: ComposedOutput, RenderedImage 모델
- `assembler.py`: 전체 조합 파이프라인 (텍스트+이미지→HTML+PNG)
- `renderer.py`: Playwright HTML→PNG (680px, 2x 레티나)
- `naver_formatter.py`: 마크다운→네이버 에디터 HTML (인라인 CSS만)

## 네이버 에디터 호환
- `<style>` 태그 금지 → 모든 CSS를 인라인 style 속성으로
- 폰트: 나눔고딕, 맑은 고딕
- 줄간격: line-height 1.8
- 이미지: `<img>` 태그에 절대 경로
- 실사 사진: 플레이스홀더로 위치만 표시 (MVP)
