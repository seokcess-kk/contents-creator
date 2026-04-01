---
name: content-composition
description: "검증 통과한 콘텐츠를 최종 HTML로 조합하고, 디자인 카드를 PNG로 렌더링하며, 네이버 블로그 에디터에 붙여넣기 최적화된 출력을 생성하는 스킬. '조합', '렌더링', '최종 출력', '네이버 에디터', 'HTML 생성', 'PNG 변환' 요청 시 이 스킬을 사용할 것."
---

# 콘텐츠 조합 및 출력

## 조합 순서

```
1. 컴플라이언스 PASS 확인
2. 디자인 카드 HTML → PNG 렌더링 (Playwright)
3. AI 이미지 프롬프트 → 이미지 생성 API 호출
4. 텍스트 + 이미지 + 플레이스홀더 → 최종 HTML 조합
5. 네이버 에디터 최적화 포맷 변환
6. Disclaimer 자동 삽입
7. 출력 파일 생성
```

## 디자인 카드 PNG 렌더링

Playwright로 HTML → PNG 변환:
```python
# 뷰포트: 680px 너비
# device_scale_factor: 2 (레티나 대응)
# 배경: 투명 또는 디자인 카드 지정 색상
# format: png
```

## 네이버 에디터 최적화

네이버 블로그 에디터(스마트에디터 3.0)에 붙여넣기 호환을 위한 규칙:
- CSS는 반드시 인라인 스타일로 변환 (`style` 속성)
- `<style>` 태그, `<link>` 태그 사용 금지 (에디터가 제거함)
- 이미지는 `<img>` 태그에 절대 URL 또는 로컬 경로
- 폰트: 나눔고딕, 맑은 고딕 등 시스템 폰트 지정
- 줄간격: `line-height: 1.8` (네이버 블로그 가독성 기준)
- 문단 간격: `margin-bottom: 20px`

## 실사 사진 플레이스홀더

MVP에서 실사 사진은 사용자가 수동 삽입한다. 위치 표시:
```html
<div style="border: 2px dashed #ccc; padding: 40px; text-align: center; color: #999; margin: 20px 0;">
  📷 실사 사진 삽입 위치 — [원장 프로필 사진] / [시술실 사진] / [전후 사진]
</div>
```

## 최종 출력 구조

```
output/{keyword}_{YYYYMMDD_HHMMSS}/
├── final.html           ← 전체 HTML (이미지 포함)
├── paste_ready.html     ← 네이버 에디터 붙여넣기용
├── images/
│   ├── header.png
│   ├── cta.png
│   └── ai_01.png ...
└── summary.json         ← 메타: 키워드, 프로필, 변이 조합, 검증 결과
```
