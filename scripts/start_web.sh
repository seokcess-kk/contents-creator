#!/usr/bin/env bash
# Contents Creator 웹 UI 시작 스크립트
# FastAPI 백엔드 + Next.js 프론트엔드를 동시에 실행한다.
#
# 사용법:
#   bash scripts/start_web.sh          # 개발 모드
#   bash scripts/start_web.sh --prod   # 프로덕션 모드

set -euo pipefail
cd "$(dirname "$0")/.."

PROD=false
[[ "${1:-}" == "--prod" ]] && PROD=true

cleanup() {
    echo "Shutting down..."
    kill $API_PID $FRONT_PID 2>/dev/null || true
    wait $API_PID $FRONT_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting FastAPI backend on :8000 ..."
python -m uvicorn web.api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "Starting Next.js frontend on :3000 ..."
if [ "$PROD" = true ]; then
    cd web/frontend
    npx next build
    npx next start -p 3000 &
    FRONT_PID=$!
    cd ../..
else
    cd web/frontend
    npx next dev -p 3000 &
    FRONT_PID=$!
    cd ../..
fi

echo ""
echo "============================================"
echo "  Contents Creator Web UI"
echo "  Frontend: http://localhost:3000"
echo "  API docs: http://localhost:8000/docs"
echo "============================================"
echo ""

wait
