@echo off
REM Contents Creator 웹 UI 시작 (Windows)
REM Terminal 2개에서 각각 실행하거나 이 스크립트를 사용.

cd /d "%~dp0\.."

echo Starting FastAPI backend on :8000 ...
start "FastAPI" cmd /c "python -m uvicorn web.api.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Next.js frontend on :3000 ...
start "Next.js" cmd /c "cd web\frontend && npx next dev -p 3000"

echo.
echo ============================================
echo   Contents Creator Web UI
echo   Frontend: http://localhost:3000
echo   API docs: http://localhost:8000/docs
echo ============================================
echo.
