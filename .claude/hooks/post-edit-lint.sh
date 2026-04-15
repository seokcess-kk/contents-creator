#!/usr/bin/env bash
# Post-edit lint for contents-creator project
#
# 책임:
# 1. domain/generation/body_writer.py 수정 시 M2 불변 규칙 검사
#    — intro 원문이 유입되지 않았는지 grep으로 확인
# 2. domain/generation/*.py 가 prompt_builder를 우회하지 않는지 검사
# 3. domain/* 외부에서 의료법 금지 표현 하드코딩 검사
#    — 금지 표현 리스트는 domain/compliance/rules.py 를 단일 출처로 동적 로드
#    — rules.py 가 아직 없거나 import 실패 시 이 검사는 조용히 스킵
#
# 호출:
#   .claude/hooks/post-edit-lint.sh <edited_file_path>
#
# Exit codes:
#   0 — 통과
#   1 — 위반 감지

set -euo pipefail

# Claude Code 2.1+ 는 훅에 JSON 을 stdin 으로 전달한다.
# `tool_input.file_path` 에 편집된 파일 경로가 있다.
# stdin 이 없으면(직접 실행) $1 로 폴백.
if [ ! -t 0 ]; then
  FILE=$(python -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('tool_input', {}).get('file_path', ''))" 2>/dev/null || echo "")
else
  FILE="${1:-}"
fi

if [[ -z "$FILE" ]]; then
  exit 0
fi

# 진단용 로그 (gitignore 대상). 훅이 실제로 호출되는지 확인하는 용도.
DEBUG_LOG="dev/active/hook-debug.log"
mkdir -p "$(dirname "$DEBUG_LOG")" 2>/dev/null || true
printf '%s FILE=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$FILE" >> "$DEBUG_LOG" 2>/dev/null || true

# 절대 경로를 프로젝트 상대 경로로 정규화
REL_FILE="${FILE#*/contents-creator/}"

# 디렉토리나 존재하지 않는 파일은 스킵
if [[ ! -f "$FILE" ]]; then
  exit 0
fi

violations=()

# ============================================================
# R1 — M2: body_writer는 intro 원문을 받지 않는다
# ============================================================
if [[ "$REL_FILE" == domain/generation/body_writer.py ]]; then
  # 금지 식별자 패턴 (intro_tone_hint 는 허용이므로 제외)
  forbidden_identifiers=(
    'intro_text'
    'intro_md'
    'full_intro'
    'intro_content'
    'intro_body'
    'intro_raw'
  )

  for pat in "${forbidden_identifiers[@]}"; do
    if grep -n "$pat" "$FILE" > /dev/null 2>&1; then
      violations+=("[R1/M2] body_writer.py contains forbidden identifier: '$pat'. Only 'intro_tone_hint' is allowed.")
    fi
  done

  # 한글 '도입부' 키워드가 문자열 리터럴에 있는지 확인
  if grep -nE '"[^"]*도입부[^"]*"|\x27[^\x27]*도입부[^\x27]*\x27' "$FILE" > /dev/null 2>&1; then
    violations+=("[R1/M2] body_writer.py contains '도입부' in a string literal. Intro must not appear in body_writer prompts.")
  fi
fi

# ============================================================
# R2 — prompt_builder 단일 진입점
# ============================================================
if [[ "$REL_FILE" == domain/generation/body_writer.py ]] || \
   [[ "$REL_FILE" == domain/generation/outline_writer.py ]]; then
  if grep -nE 'messages=\[' "$FILE" > /dev/null 2>&1; then
    if ! grep -nE 'from .*prompt_builder import|from .prompt_builder' "$FILE" > /dev/null 2>&1; then
      violations+=("[R2] $REL_FILE calls LLM (messages=[...]) but does not import from prompt_builder. Prompts must be built via prompt_builder.")
    fi
  fi
fi

# ============================================================
# R3 — 의료법 금지 표현 하드코딩 검사 (rules.py 단일 출처)
#
# domain/compliance/rules.py 의 FORBIDDEN_LITERALS 를 동적으로 로드하여
# domain/* 의 다른 파일에 해당 표현이 문자열 리터럴로 존재하는지 검사한다.
#
# rules.py 가 없거나 import 실패 시 → 조용히 스킵 (스캐폴딩 단계 허용)
# ============================================================
if [[ "$REL_FILE" == domain/* ]] && \
   [[ "$REL_FILE" != domain/compliance/rules.py ]] && \
   [[ "$REL_FILE" != */__init__.py ]] && \
   [[ -f domain/compliance/rules.py ]]; then

  # rules.py 에서 FORBIDDEN_LITERALS 동적 로드 (실패 시 빈 문자열)
  literals=$(python -c "
import sys
try:
    from domain.compliance.rules import FORBIDDEN_LITERALS
    for s in FORBIDDEN_LITERALS:
        print(s)
except Exception:
    pass
" 2>/dev/null || true)

  if [[ -n "$literals" ]]; then
    while IFS= read -r expr; do
      [[ -z "$expr" ]] && continue
      # 이스케이프가 필요한 특수 문자 처리
      esc=$(printf '%s' "$expr" | sed 's/[][\.*^$/]/\\&/g')
      if grep -nE "[\"']${esc}[\"']" "$FILE" > /dev/null 2>&1; then
        violations+=("[R3] $REL_FILE hardcodes prohibited expression '$expr'. Define in domain/compliance/rules.py only.")
      fi
    done <<< "$literals"
  fi
fi

# ============================================================
# 결과 리포트
# ============================================================
if [[ ${#violations[@]} -gt 0 ]]; then
  echo "⚠️  post-edit-lint found violations in $REL_FILE:"
  printf '   %s\n' "${violations[@]}"
  echo ""
  echo "References:"
  echo "  - SPEC.md §3 [7] (M2 rule)"
  echo "  - .claude/skills/generation/SKILL.md"
  echo "  - .claude/skills/medical-compliance/SKILL.md"
  exit 1
fi

exit 0
