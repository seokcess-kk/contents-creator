# Lessons — 실수 패턴 & 교훈

> 사용자 교정이나 반복 실수 발견 시 이 파일에 기록.
> 세션 시작 시 이 파일을 리뷰. 반복 패턴 발견 시 `CLAUDE.md` 에 규칙으로 승격.

## 실측 결과 (Phase 0.5)

### [B3] 네이버 스마트에디터 HTML 호환성 (2026-04-15 실측 완료)

**테스트 방법**: `dev/active/naver-compat-test.html` 를 브라우저에서 렌더링 → `Ctrl+A` `Ctrl+C` → 네이버 스마트에디터 ONE 본문에 `Ctrl+V` → 결과 관찰.

**결과**:

| 요소 | 보존 | 비고 |
|---|---|---|
| `<h2>`, `<h3>` | ✅ | 제목 서식 유지 |
| `<p>` | ✅ | 일반 문단 |
| `<strong>`, `<em>` | ✅ | 인라인 굵게/기울임 |
| `<hr>` | ✅ | 구분선 요소 |
| 단일 `<ul>` | ✅ | 불릿 리스트 |
| 단일 `<ol>` | ✅ | 번호 리스트 |
| `<blockquote>` | ✅ | 인용구 |
| `<table>` / `<thead>` / `<tbody>` / `<tr>` / `<th>` / `<td>` | ✅ | 표 구조 유지 |
| **중첩 `<ul>` / `<ol>`** | ❌ | **네이버 에디터가 평탄화하거나 소실** |

**확정된 화이트리스트** (`domain/composer/naver_html.py` `ALLOWED_TAGS`):
```python
ALLOWED_TAGS = {
    "h2", "h3", "p", "strong", "em", "hr",
    "ul", "ol", "li",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
}
```

**리스트 중첩 제약**:
- 생성 단계([6][7]) 프롬프트에 "리스트를 중첩하지 말 것" 지시 추가
- 조립 단계([9]) `naver_html.py` 에서 중첩 리스트 감지 시 경고 로그 (`logging.warning`) 남기고 평탄화
- 분석 단계([3]) 에서는 입력 블로그가 중첩 리스트를 써도 정상 파싱 (입력 데이터는 그대로 유지)

**재발 방지**:
- 화이트리스트 상수는 `naver_html.py` 에만 정의 (단일 출처)
- 중첩 리스트 금지 규칙은 SPEC.md §3 [6][7] 및 generation 스킬에 명시
- 에디터 버전이 바뀌면 이 실측을 재수행하고 `lessons.md` 를 업데이트

### [C1] Bright Data Web Unlocker iframe 처리 (2026-04-15 실측 완료)

**결론: 모바일 URL (`m.blog.naver.com/{id}/{no}`) 은 단일 호출로 본문 fetch 가능. 데스크톱 URL 은 iframe 껍데기만 반환되어 2단계 호출 필요.**

| URL 패턴 | Body | iframe | 본문 컨테이너 | 호출 횟수 |
|---|---|---|---|---|
| `blog.naver.com/{id}/{no}` | 3KB | 1개 | 없음 | 2번 필요 |
| `m.blog.naver.com/{id}/{no}` | 129KB | 0개 | `se-main-container`, `se_component`, `post_ct`, `__se_module_data` 모두 존재 | **1번 OK** |

**적용 방침**: `domain/crawler/page_scraper.py` 는 입력 URL 을 받으면 `blog.naver.com` → `m.blog.naver.com` 으로 정규화한 뒤 Web Unlocker 호출. 단일 호출로 끝남.

**부가 발견**:
- 일반 포스트 URL 패턴은 `blog.naver.com/{blogId}/{10자리 이상 숫자 postNo}` (예: `/ssmaa/224246591163`)
- SERP 응답에는 `/clip/` (동영상 클립) URL 도 섞여 있으므로 필터링 시 `clip` 경로 제외 필요
- 정규식 권장: `https?://(?:m\.)?blog\.naver\.com/[a-zA-Z0-9_-]+/\d{9,}` (clip 과 유저 홈 배제)

**영향**:
- SPEC.md §3 [2] iframe 처리 로직을 "모바일 정규화 후 단일 호출" 로 확정
- crawling 스킬 업데이트
- `BRIGHT_DATA_API_KEY` 는 `7243a70f-16c...` (검증용 prefix)

### [C3] Claude Code 훅 환경 변수 (2026-04-15 실측 완료)

**결론: `$CLAUDE_FILE_PATH` 같은 환경 변수는 존재하지 않는다. Claude Code 2.1+ 는 훅에 JSON 을 stdin 으로 전달한다.**

**전달 구조**: stdin 으로 한 줄 JSON
```json
{"tool_name": "Edit", "tool_input": {"file_path": "절대경로", ...}, "tool_response": {...}}
```

**파일 경로 추출 방법**:
- `.tool_input.file_path` (편집 전 알려진 경로)
- `.tool_response.filePath` (편집 후 실제 경로)
- 파싱: `jq` 가 표준이지만 Windows 에서는 Python 사용 (`python -c "import sys, json; print(json.loads(sys.stdin.read())['tool_input']['file_path'])"`)

**settings.json 올바른 형식**:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{"type": "command", "command": "bash .claude/hooks/post-edit-lint.sh"}]
    }]
  }
}
```
(command 에 `$VARIABLE` 안 넣음. 훅 스크립트가 stdin 직접 파싱)

**검증 방법**: `post-edit-lint.sh` 에 진단 로그 `dev/active/hook-debug.log` 를 추가 → 아무 파일 Edit → 로그에 절대 경로가 기록되는지 확인. 4개 파일 Edit 모두 정상 기록 확인 완료.

**참조**: [Claude Code Hooks 공식 문서](https://code.claude.com/docs/en/hooks)

## 설계 결정

### Bright Data — SERP API 대신 Web Unlocker 단일 zone (2026-04-15)

**발견**: Bright Data SERP API 는 전용 파서를 제공하는 검색 엔진이 Google / Bing / Yandex / Baidu 로 한정되어 있고 **Naver 는 지원하지 않는다** (대시보드의 검색 엔진 드롭다운에 Google 만 노출).

**결정**: SERP 수집과 본문 수집을 모두 **Web Unlocker 단일 zone** 으로 처리한다.
- Web Unlocker 는 범용 fetcher 이므로 네이버 검색 결과 페이지 (`search.naver.com/search.naver?query=...&where=blog`) 도 그대로 fetch 된다
- 응답 HTML 을 BeautifulSoup 으로 직접 파싱해 블로그 URL 리스트 추출
- 본문 수집은 동일 zone 으로 블로그 URL 호출
- SERP API 의 구조화 JSON 파싱 기능은 어차피 필요 없으므로 손실 없음

**영향**:
- `config/.env`: `BRIGHT_DATA_SERP_ZONE` 제거, `BRIGHT_DATA_WEB_UNLOCKER_ZONE` 단일 사용
- `config/settings.py`: `bright_data_serp_zone` 필드 제거
- SPEC.md §3 [1] 업데이트 (Web Unlocker + BS4 파싱으로 전환)
- crawling 스킬 업데이트

**재발 방지**: 서드파티 API 의 전용 지원 목록을 SPEC 착수 전 반드시 확인한다. "이 서비스에서 X 기능이 있다" 와 "우리 대상 서비스에 X 기능이 작동한다" 는 별개.

## 실수 패턴

### Supabase `public` 스키마 리셋 후 권한 누락 (2026-04-15)

**증상**: `service_role` 키로도 `permission denied for table X` 에러 (42501)

**원인**: `drop schema public cascade; create schema public;` 후 `grant usage on schema public to ...` 만 복원하고, **테이블 레벨 권한과 default privileges 복원을 빼먹음**. 그 결과 서비스 역할에 새 테이블 접근 권한이 없음.

**해결**: `config/schema.sql` 실행 시 다음을 함께 수행
```sql
grant all on all tables in schema public to postgres, anon, authenticated, service_role;
grant all on all sequences in schema public to postgres, anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to postgres, anon, authenticated, service_role;
-- ...
```

**재발 방지**: `config/schema.sql` 하단에 GRANT/ALTER DEFAULT PRIVILEGES 구문을 항상 포함한다. public 스키마 리셋 절차는 Supabase 공식 예시를 따른다.

## 참고 패턴

_(유용한 패턴이나 관례를 기록)_
