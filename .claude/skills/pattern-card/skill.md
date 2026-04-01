---
name: pattern-card
description: "텍스트+비주얼 분석 결과를 통합하여 키워드별 패턴 카드를 생성하는 스킬. 패턴 카드는 콘텐츠 생성의 뼈대(구조적 제약)와 살(자유 영역)을 정의하는 핵심 자산이다. '패턴 카드 생성', '분석 결과 종합', '패턴 통합' 요청 시 이 스킬을 사용할 것."
---

# 패턴 카드 생성

## 패턴 카드란

키워드별 상위 노출 콘텐츠의 공통 패턴을 정형화한 데이터. 1번 생성 후 N번 재사용하는 자산이다. "분석 1번, 생성 N번" 원칙의 핵심.

## 통합 로직

text_analysis.json과 visual_analysis.json을 입력받아 하나의 pattern_card.json을 생성한다.

**텍스트 패턴 추출:**
- 글자수 범위: 개별 포스트 글자수의 P25~P75 (사분위수)
- 소제목 수: 최빈값 ±1
- 제목 공식: 상위 2~3개 패턴 + 대표 템플릿
- 훅 유형: 분포 상위 2개
- 설득 구조: 최다 유형 1개
- 필수 키워드: 상위글 70% 이상에서 공통 등장하는 키워드
- 연관 키워드: L2에서 추출된 LSI 키워드 상위 10개

**비주얼 패턴 추출:**
- 색상 팔레트: DOM dominant palette 상위 3~5색
- 레이아웃: VLM 분류 최빈 패턴
- 이미지 유형 비율: VLM 분류 결과 집계
- 이미지 수 범위: P25~P75

## 뼈대 vs 살 구분

**뼈대 (패턴 카드가 강제하는 것):**
- section_order, char_range, subtitle_count
- title_formulas, required_keywords
- color_palette, layout_pattern, image_count_range

**살 (생성 시 자유롭게 변이하는 것):**
- 구체적 문장, 어휘 선택
- 도입부 스토리/에피소드
- 사례·후기 디테일
- 소제목 실제 문구

이 구분을 pattern_card.json의 `constraints` 필드에 명시하여 content-writer가 참조한다.

## 품질 기준

- 분석 포스트 수 N개 중 유효 분석이 50% 미만이면 `confidence: "low"` 표시
- 패턴 분포가 균등하여 우세 패턴이 없으면 상위 2개를 병렬 제시
- incomplete 플래그가 있는 분석(한쪽만 성공)은 가중치를 낮춰 반영
