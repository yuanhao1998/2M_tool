#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "正在停止服务..."
  kill $BACKEND_PID 2>/dev/null
  kill $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID 2>/dev/null
  wait $FRONTEND_PID 2>/dev/null
  echo "已停止"
}
trap cleanup EXIT INT TERM

echo "=== 启动后端 (FastAPI) ==="
cd "$SCRIPT_DIR/backend"
pip install -r requirements.txt -q 2>/dev/null
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "=== 启动前端 (Vite) ==="
cd "$SCRIPT_DIR/frontend"
npm install --silent 2>/dev/null
npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "后端: http://0.0.0.0:8000"
echo "前端: http://0.0.0.0:5173"
echo "按 Ctrl+C 停止所有服务"
echo ""

wait
