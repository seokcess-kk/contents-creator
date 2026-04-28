#!/usr/bin/env bash
# Build check for contents-creator project
#
# CLAUDE.md 검증 규칙의 "코드 변경 후 필수 수행" 순서를 실행:
#   1. ruff check .
#   2. ruff format --check .
#   3. architecture-check.sh
#   4. pyright (basic 모드, pyrightconfig.json 사용)
#   5. pytest -q
#
# 2026-04-28: mypy → pyright 전환.
# 사유: (1) mypy DLL load 실패가 Windows Python 3.13 환경에서 산발적 발생,
#       (2) anthropic SDK 타입 업데이트로 strict mode 46 사전 에러 누적,
#       (3) pyright 는 Node.js 단일 바이너리로 cross-platform 안정,
#       (4) basic 모드 + 프로젝트별 reportXxx 조정으로 점진적 강화 가능.
# pyrightconfig.json 이 단일 출처 — pyproject.toml [tool.mypy] 는 더 엄격한
# 검사를 원하는 개발자가 수동으로 사용 가능 (선택적).
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

# pyright — pyrightconfig.json 의 include/exclude/typeCheckingMode 사용.
# 미설치 환경 대응: 자동 SKIP.
if command -v pyright >/dev/null 2>&1; then
  step "pyright" pyright
else
  echo "━━━ pyright — SKIP (미설치). pip install pyright 권장 ━━━"
fi

# pytest는 tests/ 디렉토리가 존재할 때만 실행
if [[ -d tests ]]; then
  step "pytest" pytest -q
else
  echo "━━━ pytest — SKIP (tests/ 없음) ━━━"
fi

# frontend vitest — package.json 에 test script 가 있고 node_modules 가 존재할 때만.
# (CI 가 npm install 한 환경에서만 실행 — 로컬 미설치 시 SKIP)
if [[ -f web/frontend/package.json ]] && [[ -d web/frontend/node_modules ]] && \
   grep -q '"test"' web/frontend/package.json; then
  step "vitest" bash -c "cd web/frontend && npm test --silent"
else
  echo "━━━ vitest — SKIP (web/frontend/node_modules 없음 또는 test 스크립트 부재) ━━━"
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
