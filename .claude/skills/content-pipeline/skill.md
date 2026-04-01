---
name: content-pipeline
description: "네이버 블로그 SEO 콘텐츠 생성 전체 파이프라인을 오케스트레이션하는 스킬. 크롤링 → 분석(텍스트+비주얼 병렬) → 패턴카드 → 콘텐츠 생성 → 의료법 검증 → 최종 조합까지 전 과정을 에이전트 팀으로 조율한다. '파이프라인 실행', '콘텐츠 생성 전체', '전체 실행', '키워드로 블로그 글 만들어줘' 요청 시 반드시 이 스킬을 사용할 것."
---

# 콘텐츠 생성 파이프라인 오케스트레이터

**실행 모드:** 에이전트 팀 (팀 재구성 패턴)

## 에이전트 구성

| 에이전트 | 타입 | 역할 | 스킬 | 출력 |
|---------|------|------|------|------|
| crawler | general-purpose | 네이버 상위글 수집 | naver-crawling | _workspace/01_crawl/ |
| text-analyst | general-purpose | L1+L2 텍스트 분석 | text-analysis | _workspace/02_analysis/text_analysis.json |
| visual-analyst | general-purpose | DOM+VLM 비주얼 분석 | visual-analysis | _workspace/02_analysis/visual_analysis.json |
| pattern-synthesizer | general-purpose | 패턴 카드 생성 (리더) | pattern-card | _workspace/03_pattern/pattern_card.json |
| content-writer | general-purpose | 변이 기반 콘텐츠 생성 | content-generation | _workspace/04_content/ |
| medical-reviewer | general-purpose | 의료광고법 검증 | medical-compliance | _workspace/05_review/ |
| composer | general-purpose | 최종 조합+렌더링 | content-composition | output/ |
| profile-extractor | general-purpose | 클라이언트 프로필 자동 추출 | client-profile | _workspace/profile/ |

## 파이프라인 흐름

```
[사전] Phase 0: 클라이언트 프로필 확보 (없는 경우 자동 추출)
    ↓ client_profile (Supabase 또는 _workspace/profile/)

Phase A: 크롤링 (sub-agent, 단독)
    ↓ _workspace/01_crawl/
Phase B: 분석 팀 (fan-out/fan-in, TeamCreate)
    ├── text-analyst ──┐
    ├── visual-analyst ─┤ (병렬 → 합류)
    └── pattern-synthesizer (리더, 통합)
    ↓ _workspace/03_pattern/
Phase C: 생성+검증 팀 (producer-reviewer, TeamCreate)
    ├── content-writer (생성, 의료법 1차 방어 주입)
    └── medical-reviewer (검증 2차+3차 방어, 최대 2회 루프)
    ↓ _workspace/05_review/ (PASS)
Phase D: 조합 (sub-agent, 단독)
    ↓ output/
```

## Phase 0: 클라이언트 프로필 확보 (조건부)

클라이언트 프로필이 없는 경우에만 실행한다. Supabase에 이미 확정된 프로필이 있으면 스킵.

```
Agent(
  agent: "profile-extractor",
  model: "opus",
  prompt: "URL '{client_url}'에서 클라이언트 프로필을 자동 추출하라.
           client-profile 스킬을 참조하라.
           출력: _workspace/profile/draft_profile.json
           완료 후 사용자에게 review_prompt.md를 제시하여 확인받아라."
)
```

**완료 조건:** 사용자가 프로필을 확인·수정하여 확정 → Supabase 저장 (status: "confirmed")
**이미 프로필 있는 경우:** Supabase에서 client_id로 조회하여 바로 Phase A로 진행

## Phase A: 크롤링

crawler를 서브에이전트로 실행한다 (단독 작업, 팀 불필요).

```
Agent(
  agent: "crawler",
  model: "opus",
  prompt: "키워드 '{keyword}'로 네이버 상위 {top_n}개 블로그를 크롤링하라.
           naver-crawling 스킬을 참조하라.
           출력: _workspace/01_crawl/"
)
```

**완료 조건:** `_workspace/01_crawl/metadata.json` 존재 + posts/ 내 파일 1개 이상
**실패 시:** 크롤링 결과 0건이면 파이프라인 중단, 사용자에게 키워드 재입력 요청

## Phase B: 분석 팀 (Fan-out / Fan-in)

Phase A 완료 후 팀을 구성한다.

```
TeamCreate(
  team_name: "analysis-team",
  members: ["text-analyst", "visual-analyst", "pattern-synthesizer"]
)
```

**작업 할당:**
```
TaskCreate([
  {
    title: "텍스트 분석 수행",
    assignee: "text-analyst",
    description: "_workspace/01_crawl/posts/*.html을 L1+L2 분석.
                  text-analysis 스킬 참조.
                  출력: _workspace/02_analysis/text_analysis.json"
  },
  {
    title: "비주얼 분석 수행",
    assignee: "visual-analyst",
    description: "_workspace/01_crawl/posts/ 의 HTML+PNG를 DOM+VLM 분석.
                  visual-analysis 스킬 참조.
                  출력: _workspace/02_analysis/visual_analysis.json"
  },
  {
    title: "패턴 카드 생성",
    assignee: "pattern-synthesizer",
    depends_on: ["텍스트 분석 수행", "비주얼 분석 수행"],
    description: "text_analysis.json + visual_analysis.json 통합하여 패턴 카드 생성.
                  pattern-card 스킬 참조.
                  출력: _workspace/03_pattern/pattern_card.json"
  }
])
```

**팀 통신 규칙:**
- text-analyst ↔ visual-analyst: 상관관계 발견 시 SendMessage로 공유
- 양쪽 → pattern-synthesizer: 완료 시 SendMessage로 알림
- pattern-synthesizer: 양쪽 완료 대기 후 통합 작업 시작

**완료 조건:** `_workspace/03_pattern/pattern_card.json` 존재
**완료 후:** TeamDelete("analysis-team")

## Phase C: 생성+검증 팀 (Producer-Reviewer)

Phase B 완료 후 새 팀을 구성한다.

```
TeamCreate(
  team_name: "production-team",
  members: ["content-writer", "medical-reviewer"]
)
```

**작업 할당:**
```
TaskCreate([
  {
    title: "콘텐츠 생성",
    assignee: "content-writer",
    description: "패턴 카드(_workspace/03_pattern/pattern_card.json) +
                  클라이언트 프로필을 결합하여 콘텐츠 생성.
                  content-generation 스킬 참조.
                  [1차 방어] 의료 업종인 경우 medical-compliance 스킬의
                  prohibited-expressions.md를 LLM 프롬프트에 주입.
                  [승인] 변이 조합을 사용자에게 제시하고 승인 후 생성.
                  출력: _workspace/04_content/
                  완료 후 medical-reviewer에게 SendMessage로 검증 요청."
  },
  {
    title: "의료법 검증",
    assignee: "medical-reviewer",
    depends_on: ["콘텐츠 생성"],
    description: "_workspace/04_content/ 의 모든 텍스트를 의료광고법 기준으로 검증.
                  medical-compliance 스킬 참조.
                  출력: _workspace/05_review/compliance_report.json
                  PASS → 오케스트레이터에게 알림.
                  FIX → content-writer에게 수정 지시 (SendMessage + violations 목록)."
  }
])
```

**Producer-Reviewer 루프:**
```
content-writer 생성 → medical-reviewer 검증
    ├── PASS → Phase D로 진행
    ├── FIX → content-writer에게 수정 지시 → 재생성 → 재검증 (최대 2회)
    └── REJECT → 파이프라인 중단, 사용자에게 보고
```

**최대 2회 수정 루프.** 3회째 FIX 판정 시:
- 현재 버전 + 미해결 violations 목록을 사용자에게 보고
- 사용자 판단: 수동 수정 or 파이프라인 재실행

**완료 조건:** `compliance_report.json`의 verdict가 "PASS"
**완료 후:** TeamDelete("production-team")

## Phase D: 최종 조합

Phase C 완료 후 composer를 서브에이전트로 실행한다.

```
Agent(
  agent: "composer",
  model: "opus",
  prompt: "검증 통과한 콘텐츠를 최종 조합하라.
           입력: _workspace/04_content/ + _workspace/05_review/
           content-composition 스킬 참조.
           출력: output/{keyword}_{timestamp}/"
)
```

**완료 조건:** `output/` 내 final.html + paste_ready.html 존재
**실패 시:** 렌더링 실패한 이미지는 HTML 원본 보존, 사용자에게 수동 렌더링 안내

## 데이터 흐름 다이어그램

```
[입력]
  keyword: string
  top_n: int (기본 10)
  client_profile: object (Supabase ID 또는 직접 전달)

Phase A ─→ _workspace/01_crawl/
              ├── metadata.json
              └── posts/{nn}_raw.html, {nn}_screenshot.png

Phase B ─→ _workspace/02_analysis/
              ├── text_analysis.json
              └── visual_analysis.json
         ─→ _workspace/03_pattern/
              └── pattern_card.json

Phase C ─→ _workspace/04_content/
              ├── seo_text.md
              ├── variation_config.json
              ├── design_cards/header.html, cta.html
              └── ai_image_prompts/prompts.json
         ─→ _workspace/05_review/
              └── compliance_report.json

Phase D ─→ output/{keyword}_{timestamp}/
              ├── final.html
              ├── paste_ready.html
              ├── images/header.png, cta.png, ai_*.png
              └── summary.json
```

## 에러 핸들링

| 상황 | 대응 |
|------|------|
| Phase A 크롤링 0건 | 파이프라인 중단, 키워드 변경 안내 |
| Phase B 한쪽 분석 실패 | 성공한 분석만으로 부분 패턴 카드 생성 (confidence: low) |
| Phase B 양쪽 모두 실패 | 파이프라인 중단, 크롤링 데이터 확인 안내 |
| Phase C 3회 FIX | 현재 버전 + 미해결 목록 보고, 사용자 판단 |
| Phase C REJECT | 파이프라인 중단, 패턴 카드 또는 프로필 수정 안내 |
| Phase D 렌더링 실패 | HTML 원본 보존, 수동 렌더링 안내 |
| LLM API 장애 | 해당 Phase에서 1회 재시도 → 실패 시 가능한 결과만 반환 |

## 테스트 시나리오

### 정상 흐름
```
입력: keyword="강남 피부과 여드름", top_n=5, client_profile={강남피부과 프로필}

1. Phase A: 5개 블로그 크롤링 성공 (metadata.json + 5개 HTML/PNG)
2. Phase B:
   - text-analyst: L1+L2 분석 완료 (text_analysis.json)
   - visual-analyst: DOM+VLM 분석 완료 (visual_analysis.json)
   - pattern-synthesizer: 패턴 카드 생성 (pattern_card.json)
3. Phase C:
   - content-writer: SEO 텍스트 + 디자인 카드 HTML 생성
   - medical-reviewer: 1차 검증 → FIX (2건 CRITICAL)
   - content-writer: 수정 후 재전달
   - medical-reviewer: 2차 검증 → PASS
4. Phase D: 최종 HTML 조합 + PNG 렌더링 + 네이버 에디터 출력

출력: output/강남_피부과_여드름_20260331_143000/
```

### 에러 흐름
```
입력: keyword="희귀 시술명", top_n=10, client_profile={...}

1. Phase A: 3개만 크롤링 성공 (7개 비공개/삭제)
2. Phase B:
   - text-analyst: 3개 분석 완료
   - visual-analyst: VLM API 실패 → DOM 결과만 반환
   - pattern-synthesizer: 부분 패턴 카드 생성 (confidence: low)
3. Phase C:
   - content-writer: 생성 완료
   - medical-reviewer: 1차 FIX → 수정 → 2차 FIX → 수정 → 3차 FIX
   - 루프 한도 초과 → 현재 버전 + 미해결 violations 사용자 보고
4. Phase D: 실행하지 않음 (사용자 판단 대기)
```
