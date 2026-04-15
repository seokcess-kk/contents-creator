---
name: medical-compliance
description: 생성된 SEO 원고를 의료광고법 제56조·제57조·시행령 제23조 기반 8개 위반 카테고리로 검증하고, 위반 발견 시 자동 수정 후 재검증하는 3중 방어 스킬. 의료·병원·한의원·피부과·치과·시술·치료 관련 콘텐츠를 생성하거나 수정할 때 반드시 이 스킬을 사용할 것. '의료법 검증', '컴플라이언스 체크', '광고법 검토', '의료 콘텐츠 검증' 요청 시에도 사용.
---

# Medical Compliance Skill — 3중 방어

의료 콘텐츠의 의료광고법 준수를 강제한다. SPEC-SEO-TEXT.md §3 [8]을 구현한다.

## 3중 방어 구조

| 방어 | 시점 | 담당 |
|---|---|---|
| **1차 (사전 주입)** | [6][7] 생성 시 | `prompt_builder.py` — 프롬프트에 금지 표현 규칙 주입 |
| **2차 (사후 검증)** | [8] 원고 완성 후 | `checker.py` — 규칙 기반 1차 + LLM 2차 |
| **3차 (자동 수정)** | 위반 발견 시 | `fixer.py` — 구절 치환 우선, 실패 시 해당 문단 재생성 (최대 2회) |

### fixer 동작 방식 (상세)

1. **기본: 구절 치환 (phrase replacement)** — 위반 표현 자리만 안전 대체어로 교체. 주변 문맥·톤을 유지하며 가장 빠르고 안전한 방식. 대부분의 케이스는 이것으로 해결.
2. **폴백: 해당 문단만 재생성** — 구절 치환 결과가 LLM 자연스러움 검사에서 실패한 경우에만 문단 단위 재생성. **도입부는 재생성 대상 아님** (M2 톤 락 원칙). 도입부가 위반이면 치환만 시도하고 실패 시 파이프라인 실패로 종료.
3. **전체 본문 재생성 금지** — fixer는 항상 국소 수정. 본문 전체를 LLM에게 다시 생성시키지 않는다.

## 8개 위반 카테고리

**⚠️ 현재 카테고리 상세 정의는 사용자 제공 대기 중**. 5단계 착수 전 `domain/compliance/rules.py`에 주입된다.

카테고리 슬롯 (코드 레벨에서 미리 예약):

```python
# domain/compliance/rules.py
from enum import Enum

class ViolationCategory(str, Enum):
    CATEGORY_1 = "category_1"  # TODO: 사용자 제공
    CATEGORY_2 = "category_2"
    CATEGORY_3 = "category_3"
    CATEGORY_4 = "category_4"
    CATEGORY_5 = "category_5"
    CATEGORY_6 = "category_6"
    CATEGORY_7 = "category_7"
    CATEGORY_8 = "category_8"
```

사용자 제공 시점에 enum 이름·regex·LLM 지시문 일괄 교체.

## rules.py 단일 출처 원칙

- 모든 금지 표현 regex는 `rules.py`에만 정의
- `checker.py`, `fixer.py`, `prompt_builder.py`는 `rules.py`를 **참조만** 하고 자체 정의하지 않는다
- 새 위반 케이스 발견 시 `rules.py`에만 추가
- `rules.py` 는 `CompliancePolicy` enum 으로 복수 프로필 지원. 이 스킬의 "8개 카테고리"는 `SEO_STRICT` 프로필 기준. 브랜드 카드 트랙용 `BRAND_LENIENT` 프로필은 `SPEC-BRAND-CARD.md` §7 참조. `checker(text, policy=CompliancePolicy.SEO_STRICT)` 형태로 호출 (기본값 `SEO_STRICT`)

## [8] 검증 파이프라인

```
full_text = intro + body_sections  (composer가 조립)
    ↓
[2-1] 규칙 기반 1차 스크리닝
  - rules.py의 regex 적용
  - 명확한 위반(예: "100% 완치") 즉시 감지
    ↓
[2-2] LLM 검증 (Sonnet 4.6, tool_use)
  - 애매한 표현 판단 (예: 암시적 보장, 비교 뉘앙스)
  - 규칙 기반이 놓친 케이스 포착
    ↓
위반 발견? ─ No → 통과
            └ Yes → [3] 자동 수정
    ↓
[3] fixer.py가 위반 문단만 교체
  - LLM에게 위반 카테고리 + 원문 + 대안 지시 → 수정안 생성
  - 해당 문단만 전체 텍스트에서 교체
    ↓
재검증 (최대 2회 반복)
    ↓
  통과 → compliance-report.json 저장, 성공 종료
  2회 후 실패 → 위반 기록 남기고 실패 종료 (파이프라인 실패)
```

## 검증 결과 구조

```json
{
  "passed": true,
  "iterations": 1,
  "violations": [],
  "changelog": [
    {
      "section": 3,
      "before": "100% 확실한 효과를 보장합니다",
      "after": "치료 효과는 개인차가 있을 수 있습니다",
      "rule": "category_X",
      "reason": "효과 보장 표현"
    }
  ],
  "final_text": "..."
}
```

저장: `output/{slug}/{timestamp}/content/compliance-report.json`

## LLM 호출 (Sonnet 4.6, tool_use)

### 검증
```python
tools = [{
    "name": "report_violations",
    "input_schema": {
        "type": "object",
        "properties": {
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": [...]},
                        "text_snippet": {"type": "string"},
                        "section_index": {"type": "integer"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "reason": {"type": "string"}
                    }
                }
            }
        }
    }
}]
```

### 수정
```python
tools = [{
    "name": "propose_fix",
    "input_schema": {
        "type": "object",
        "properties": {
            "fixed_text": {"type": "string"},
            "change_summary": {"type": "string"}
        }
    }
}]
```

## 검증 범위

| 대상 | 범위 |
|---|---|
| 원고 본문 | ✅ 필수 |
| 제목 | ✅ 필수 |
| 소제목 | ✅ 필수 |
| 디자인 카드 텍스트 | (추후 단계) |
| AI 이미지 프롬프트 | (추후 단계) |

## 타협 없음 원칙

- 의료 관련 원고 생성 시 이 스킬 경유 **의무**
- "이미지 안의 텍스트라 괜찮다"는 없음 (추후 단계 적용)
- 검증 실패 시 파이프라인 종료. 통과 없이 원고 출력 금지
- rules.py 외부에서 금지 표현 하드코딩 절대 금지

## 금지 사항

- `rules.py` 밖에서 금지 표현 regex 정의 금지
- 8개 카테고리를 늘리거나 줄이지 않는다 (사용자 확정 후 고정)
- LLM 검증을 규칙 기반 스크리닝으로 대체하거나 그 반대 금지 (둘 다 필요)
- 3회 이상 재시도 금지 (2회 후 실패로 종료)
