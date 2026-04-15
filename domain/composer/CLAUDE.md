# Composer Domain

intro + body 조립, outline.md 변환, 네이버 호환 HTML 생성. SPEC.md §3 [9] 구현.

## 핵심 규칙

### intro + body 프로그래매틱 조립 (M2 보호)

- `assembler.py` 가 `intro_text + body_sections` 를 **순수 코드로 concat**
- LLM 호출 없음. 문자열 이어붙이기만
- 결과: 마크다운 `seo-content.md`
- **M2 톤 락 유지**: [7] body_writer 가 intro 원문을 받지 않았기 때문에, 이 조립 단계가 intro 를 본문에 합치는 유일한 지점

### 네이버 호환 HTML 화이트리스트 (2026-04-15 실측 완료 ✅)

- `naver_html.py` 는 **다음 태그만 허용**:
  ```
  h2, h3, p, strong, em, hr, ul, ol, li,
  blockquote, table, thead, tbody, tr, th, td
  ```
- `class`, `style`, `script`, `iframe`, `div`, `span` 전부 제거
- `<!DOCTYPE html>` + UTF-8 meta head 래핑
- 사용자가 브라우저에서 렌더링 후 복사 → 네이버 스마트에디터에 붙여넣으면 서식 보존 (실측으로 검증됨)

### 리스트 중첩 차단

- **중첩 `<ul>`/`<ol>` 은 네이버 에디터가 소실시킨다** (B3 실측 결과)
- `naver_html.py` 는 중첩 리스트 감지 시:
  1. `logging.warning` 으로 "nested list detected at ..." 기록
  2. 중첩 항목을 부모 `<li>` 에 "• " 접두어로 평탄화 병합
- 생성 단계에서 이미 중첩을 금지하지만, 안전망으로 composer 에서도 방어

### outline.md 변환

- `outline_md.py` 가 `outline.json` → 사람 검토용 마크다운 변환
- 하단에 "## 제안 태그 (수동 삽입용)" 섹션을 추가해 `suggested_tags` 표시
- 사용자는 이 파일을 보고 네이버 에디터 태그 입력란에 수동 삽입
- **본문(`seo-content.md`/`.html`)에는 태그 미삽입**

## 파일 책임

- `assembler.py` — intro + body → `seo-content.md`
- `outline_md.py` — `outline.json` → `outline.md` (+ 태그 블록)
- `naver_html.py` — `seo-content.md` → `seo-content.html` (화이트리스트 필터)
- `model.py` — 필요 시 Pydantic 모델 (`NaverHtmlDocument` 등)

## 금지

- 본문에 태그 삽입 (태그는 메타만 유지)
- 화이트리스트 외 태그 생성
- LLM 을 조립·변환에 사용 (순수 코드로만)
- `assembler.py` 에서 intro 를 별도 재생성하거나 수정
- 화이트리스트 상수를 `naver_html.py` 외부에 중복 정의

## 참조

- @../../SPEC.md §3 [9]
- @../../.claude/skills/content-pipeline/SKILL.md (단계 매핑)
- 화이트리스트 실측 결과: `tasks/lessons.md` 참조
