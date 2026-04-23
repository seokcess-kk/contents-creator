#!/usr/bin/env bash
# Build check for contents-creator project
#
# CLAUDE.md 검증 규칙의 "코드 변경 후 필수 수행" 순서를 실행:
#   1. ruff check .
#   2. ruff format --check .
#   3. mypy domain/
#   4. pytest -q
#
# 호출:
#   .claude/hooks/build-check.sh
#
# Exit codes:
#   0 — 전부 통과
#   1 — 어느 단계라도 실패

set -euo pipefail

# 프로젝트 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

failed_steps=()

step() {
  local name="$1"
  shift
  echo ""
  echo "━━━ $name ━━━"
  if "$@"; then
    echo "✓ $name"
  else
    echo "✗ $name"
    failed_steps+=("$name")
  fi
}

step "ruff check" ruff check .
step "ruff format --check" ruff format --check .
step "architecture-check" "$SCRIPT_DIR/architecture-check.sh"

# mypy 대상: domain/ + application/ (둘 다 존재 시)
mypy_targets=()
[[ -d domain ]] && mypy_targets+=("domain/")
[[ -d application ]] && mypy_targets+=("application/")

if [[ ${#mypy_targets[@]} -gt 0 ]]; then
  step "mypy ${mypy_targets[*]}" mypy "${mypy_targets[@]}"
else
  echo "━━━ mypy — SKIP (domain/ 과 application/ 모두 없음) ━━━"
fi

# pytest는 tests/ 디렉토리가 존재할 때만 실행
if [[ -d tests ]]; then
  step "pytest" pytest -q
else
  echo "━━━ pytest — SKIP (tests/ 없음) ━━━"
fi

echo ""
if [[ ${#failed_steps[@]} -gt 0 ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  echo "✗ build-check FAILED"
  echo "  실패한 단계:"
  printf '    - %s\n' "${failed_steps[@]}"
  echo ""
  echo "  auto-error-resolver 에이전트를 호출해 원인 분석·수정·재검증을 수행하라."
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ build-check PASSED"
exit 0
