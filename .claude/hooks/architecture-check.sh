#!/usr/bin/env bash
# Architecture layering check
#
# CLAUDE.md 의 레이어 + 파이프라인 DAG 규칙을 강제:
#   - domain/ → application, web, scripts 는 import 금지 (역방향)
#   - application/ → web, scripts 는 import 금지
#   - domain 간 교차 import 는 파이프라인 DAG 방향만 허용:
#       crawler → analysis → generation → compliance → image_generation → composer
#     즉 하류 스테이지가 상류의 모델·함수를 import 하는 것은 OK,
#     상류 스테이지가 하류를 import 하는 것은 금지.
#   - domain/common/ 은 모든 도메인에서 자유롭게 import 가능
#
# 호출: .claude/hooks/architecture-check.sh
# Exit: 0 통과, 1 위반

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 파이프라인 DAG 순서 (앞쪽 = 상류).
# 하류 도메인이 자신보다 앞 번호 도메인을 import 하는 것은 허용.
declare -A STAGE_ORDER=(
  [common]=0
  [crawler]=1
  [analysis]=2
  [generation]=3
  [compliance]=4
  [image_generation]=5
  [composer]=6
  [profile]=0
)

violations=0

echo "━━━ domain → application/web/scripts 역방향 import 검사 ━━━"
if grep -rn --include='*.py' -E '^(from|import)\s+(application|web|scripts)\b' domain/ 2>/dev/null; then
  echo "✗ domain/ 내부에서 application/web/scripts 를 import 하고 있다 (역방향 금지)"
  violations=$((violations + 1))
fi

echo ""
echo "━━━ domain DAG 방향성 검사 (하류→상류만 허용) ━━━"
while IFS= read -r line; do
  file="${line%%:*}"
  rest="${line#*:}"
  own_domain="$(echo "$file" | awk -F/ '{print $2}')"
  target_domain="$(echo "$rest" | grep -oE 'domain\.[a-z_]+' | head -1 | cut -d. -f2)"
  [[ -z "$target_domain" || -z "$own_domain" ]] && continue
  [[ "$target_domain" == "$own_domain" ]] && continue
  [[ "$target_domain" == "common" || "$target_domain" == "profile" ]] && continue

  own_order="${STAGE_ORDER[$own_domain]:-}"
  target_order="${STAGE_ORDER[$target_domain]:-}"
  if [[ -z "$own_order" || -z "$target_order" ]]; then
    echo "✗ $file: 알려지지 않은 도메인 $own_domain 또는 $target_domain — STAGE_ORDER 에 등록 필요"
    violations=$((violations + 1))
    continue
  fi
  if (( target_order >= own_order )); then
    echo "✗ $file: domain/$own_domain (order=$own_order) → domain/$target_domain (order=$target_order)"
    echo "   DAG 역방향 또는 수평 교차 — 파이프라인 순서 위반"
    violations=$((violations + 1))
  fi
done < <(grep -rn --include='*.py' -E '^(from|import)\s+domain\.' domain/ 2>/dev/null || true)

echo ""
echo "━━━ application → web/scripts 역방향 import 검사 ━━━"
if grep -rn --include='*.py' -E '^(from|import)\s+(web|scripts)\b' application/ 2>/dev/null; then
  echo "✗ application/ 내부에서 web/scripts 를 import 하고 있다"
  violations=$((violations + 1))
fi

echo ""
if (( violations > 0 )); then
  echo "━━━━━━━━━━━━━━━━━━━━━━"
  echo "✗ architecture-check FAILED ($violations violation(s))"
  exit 1
fi
echo "✓ architecture-check PASSED"
exit 0
