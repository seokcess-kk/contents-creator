#!/usr/bin/env bash
# Fast build check — 변경된 .py 파일만 검사하는 빠른 피드백 모드.
#
# 풀런(build-check.sh)과의 차이:
#   - ruff / ruff format / pyright 를 변경 파일에 한정해 실행
#   - architecture-check 는 전체 (grep 기반, 1초 미만)
#   - pytest 는 SKIP — PR 직전 풀런(build-check.sh)에서 검증한다
#
# 변경 파일 산출:
#   - git diff (HEAD 기준 staged + unstaged, 삭제 제외)
#   - git ls-files --others --exclude-standard (untracked)
#
# 호출:
#   .claude/hooks/build-check-fast.sh
#
# Exit codes:
#   0 — 전부 통과 (또는 변경 .py 없음)
#   1 — 어느 단계라도 실패

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# ── 변경된 .py 파일 수집 ──────────────────────────────────────
mapfile -t CHANGED_PY < <(
  {
    git diff --name-only --diff-filter=ACMR HEAD -- '*.py' 2>/dev/null || true
    git ls-files --others --exclude-standard -- '*.py' 2>/dev/null || true
  } | sort -u
)

# 실제로 존재하는 파일만 (rename 등으로 사라진 경로 제거)
filtered=()
for f in "${CHANGED_PY[@]:-}"; do
  [[ -f "$f" ]] && filtered+=("$f")
done
CHANGED_PY=("${filtered[@]}")

if [[ ${#CHANGED_PY[@]} -eq 0 ]]; then
  echo "변경된 .py 파일 없음 — SKIP (풀런이 필요하면 build-check.sh)"
  exit 0
fi

echo "변경 파일 ${#CHANGED_PY[@]}개:"
printf '  %s\n' "${CHANGED_PY[@]}"

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

step "ruff check (변경 파일)" ruff check "${CHANGED_PY[@]}"
step "ruff format --check (변경 파일)" ruff format --check "${CHANGED_PY[@]}"
step "architecture-check" "$SCRIPT_DIR/architecture-check.sh"

# pyright — pyrightconfig.json 의 exclude(tests/scripts/web/frontend) 에 걸리는
# 변경 파일은 자동 무시됨. include 경계 밖 파일을 명시 전달해도 pyright 는 검사하므로
# 사전에 도메인 범위로 필터해 의도치 않은 검사를 막는다.
PYRIGHT_TARGETS=()
for f in "${CHANGED_PY[@]}"; do
  case "$f" in
    domain/*|application/*|config/*) PYRIGHT_TARGETS+=("$f") ;;
  esac
done

if [[ ${#PYRIGHT_TARGETS[@]} -eq 0 ]]; then
  echo ""
  echo "━━━ pyright — SKIP (domain/application/config 변경 없음) ━━━"
elif command -v pyright >/dev/null 2>&1; then
  step "pyright (변경 파일)" pyright "${PYRIGHT_TARGETS[@]}"
else
  echo ""
  echo "━━━ pyright — SKIP (미설치). pip install pyright 권장 ━━━"
fi

echo ""
echo "━━━ pytest — SKIP (fast 모드). 풀런이 필요하면 build-check.sh ━━━"

echo ""
if [[ ${#failed_steps[@]} -gt 0 ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  echo "✗ build-check-fast FAILED"
  echo "  실패한 단계:"
  printf '    - %s\n' "${failed_steps[@]}"
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ build-check-fast PASSED (pytest 는 풀런에서 검증)"
exit 0
