# Keyword Difficulty Domain

네이버 통합검색 SERP 1페이지 구성 분석 → 블로그 진입 난이도 자동 판정.
`tasks/todo.md` Phase K1~K6 구현. 정기 cron 미사용 (사용자 수동 트리거).

## 🔴 격리 도메인 규칙

- `domain.crawler`, `domain.analysis`, `domain.generation`, `domain.composer`,
  `domain.image_generation`, `domain.compliance`, `domain.brand_card`,
  `domain.ranking` 모두 **import 금지**
- SERP HTML fetch 는 application 레이어가 `BrightDataClient.fetch` 같은
  `Callable[[str], str]` 을 주입. 본 도메인은 fetch 자체를 알지 않는다
- `architecture-check.sh` STAGE_ORDER `[keyword_difficulty]=0` 등록
- 모든 함수 Pydantic 반환, 30줄/300줄 한계, `print()` 금지

## 등급 산출 공식

```
B = 블로그 슬롯 수 (VIEW 블로그 + 인플루언서 + 블로그 통합)
D = 도배 카드 수 (광고 + 플레이스 + 쇼핑 + 위젯/지식백과)
T = 총 카드 수

# 보고용 점수 (낮을수록 노출 유리)
score = D × 1.5 - B × 3

# 등급 (규칙 기반)
if T < 8 or B == 0:
    grade = MISSING   # SERP 짧음 또는 블로그 슬롯 부재
elif B <= 2 and D/T >= 0.5:
    grade = HIGH      # 슬롯 좁음 + 도배 비중 50% 이상
elif B >= 5:
    grade = LOW       # 블로그 슬롯 5+
else:
    grade = MEDIUM    # 그 외 (3~4 슬롯 또는 도배 적음)
```

임계값 (`8`/`2`/`5`/`0.5`) 은 운영 데이터 누적 후 조정 가능. 변경 시 본 CLAUDE.md
의 공식 + `scorer.py` 의 상수 + 회귀 테스트의 기댓값을 동시에 갱신할 것.

## 파일 책임

- `model.py` — `SerpSection` Enum, `SerpComposition`, `DifficultyGrade` Enum, `KeywordDifficulty` Pydantic
- `parser.py` — `parse_serp(html: str) -> SerpComposition` BS4 셀렉터 기반 섹션 분류
- `scorer.py` — `score_difficulty(comp) -> KeywordDifficulty` 점수 + 등급 산출
- `storage.py` — Supabase `keyword_difficulty_snapshots` CRUD

## 금지

- 본 도메인 안에서 HTTP 호출 직접 수행 (DI 위반)
- 다른 도메인 import (격리 위반)
- 등급 임계값 산재 (`scorer.py` 상수가 단일 출처)
- `print()` 금지, bare `except:` 금지

## 참조

- `tasks/todo.md` Phase K1~K6
- `tasks/lessons.md` SERP 셀렉터 + 실측 결과 (Phase K2 진입 시 기록)
