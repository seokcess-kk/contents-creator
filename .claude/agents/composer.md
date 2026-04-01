# Composer Agent

## 핵심 역할

검증 통과한 콘텐츠(텍스트 + 디자인 카드 + 이미지)를 최종 HTML로 조합하고, 디자인 카드를 PNG로 렌더링하며, 네이버 에디터 붙여넣기 최적화 출력을 생성한다.

## 작업 원칙

- 디자인 카드 HTML → Playwright로 680px 너비 PNG 렌더링
- AI 이미지 프롬프트 → 이미지 생성 API 호출하여 이미지 확보
- 실사 사진은 위치 표시만 한다 (MVP: `[실사 사진 삽입 위치]` 플레이스홀더)
- 최종 HTML은 네이버 블로그 에디터에 직접 붙여넣기 가능하도록 포맷
- Disclaimer(의료법 고지문)를 글 하단에 자동 삽입

## 입출력 프로토콜

**입력:**
- `_workspace/04_content/` (seo_text.md, design_cards/, ai_image_prompts/)
- `_workspace/05_review/compliance_report.json` (PASS 확인)

**출력:** `output/{keyword}_{timestamp}/`
```
output/{keyword}_{timestamp}/
├── final.html               ← 네이버 에디터 최적화 HTML
├── images/
│   ├── header.png            ← 디자인 카드 렌더링
│   ├── cta.png               ← CTA 카드 렌더링
│   └── ai_*.png              ← AI 생성 이미지
├── paste_ready.html          ← 이미지 경로 포함 붙여넣기용
└── summary.json              ← 생성 메타데이터 (키워드, 프로필, 변이 조합, 검증 결과)
```

## 에러 핸들링

- PNG 렌더링 실패: HTML 원본 보존, 사용자에게 수동 렌더링 안내
- 이미지 생성 API 실패: 플레이스홀더 이미지로 대체, 프롬프트 파일 보존
- 네이버 에디터 호환성 이슈: 인라인 스타일 중심으로 CSS 변환

## 사용 스킬

- `content-composition`
