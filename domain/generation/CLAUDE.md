# Generation 도메인 규칙

## 파일 역할
- `model.py`: GeneratedContent, VariationConfig, DesignCard 모델
- `variation_engine.py`: 5개 층위 변이 + 조합 추천
- `structure_templates.py`: 구조 템플릿 풀 (8개)
- `expression_filter.py`: AI 상투 표현 블랙리스트 + 대체
- `seo_writer.py`: Claude API SEO 텍스트 생성 (1차 방어 포함)
- `design_card.py`: 헤더/CTA 디자인 카드 HTML (680px)
- `image_generator.py`: AI 이미지 프롬프트 (인터페이스, 텍스트 삽입 금지)

## 의료법 1차 방어
- `seo_writer.py`에서 `profile.is_medical()` 체크
- True이면 MEDICAL_COMPLIANCE_INJECTION을 시스템 프롬프트에 주입
- 8개 위반 카테고리 요약 + 금지 표현 + 허용 대체 + Disclaimer 지시

## 변이 원칙
- 같은 키워드+프로필로 다중 생성 시 exclude_configs로 겹침 방지
- 패턴 카드 뼈대(구조, 글자수, 키워드)는 필수 준수
- 살(문장, 표현, 스토리)은 자유 변이
