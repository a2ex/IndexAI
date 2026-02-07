#!/bin/bash
set -e

# IndexAI — Development startup script
# Replaces docker-compose for local development

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load brew
eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  IndexAI — SEO Indexation Service      ${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. Ensure services are running
echo -e "\n${YELLOW}[1/5] Starting PostgreSQL & Redis...${NC}"
brew services start postgresql@16 2>/dev/null || true
brew services start redis 2>/dev/null || true
sleep 1

# 2. Activate venv
echo -e "${YELLOW}[2/5] Activating Python environment...${NC}"
source .venv/bin/activate

# 3. Run migrations
echo -e "${YELLOW}[3/5] Running database migrations...${NC}"
cd backend
alembic upgrade head 2>&1 | grep -v "^$"
cd ..

# 4. Start backend + Celery in background
echo -e "${YELLOW}[4/5] Starting backend services...${NC}"

# Kill any existing processes on our ports
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo -e "  ${GREEN}Backend API started (PID: $BACKEND_PID) → http://localhost:8000${NC}"

celery -A celery_app worker --loglevel=info --concurrency=2 &
WORKER_PID=$!
echo -e "  ${GREEN}Celery worker started (PID: $WORKER_PID)${NC}"

celery -A celery_app beat --loglevel=info &
BEAT_PID=$!
echo -e "  ${GREEN}Celery beat started (PID: $BEAT_PID)${NC}"
cd ..

# 5. Start frontend
echo -e "${YELLOW}[5/5] Starting frontend...${NC}"
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true

cd frontend
npm run dev &
FRONTEND_PID=$!
echo -e "  ${GREEN}Frontend started (PID: $FRONTEND_PID) → http://localhost:3000${NC}"
cd ..

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  All services running!                 ${NC}"
echo -e "${GREEN}  Frontend:  http://localhost:3000       ${NC}"
echo -e "${GREEN}  API:       http://localhost:8000       ${NC}"
echo -e "${GREEN}  API Docs:  http://localhost:8000/docs  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Trap Ctrl+C to kill all background processes
cleanup() {
    echo -e "\n${YELLOW}Stopping all services...${NC}"
    kill $BACKEND_PID $WORKER_PID $BEAT_PID $FRONTEND_PID 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for any background process to finish
wait
