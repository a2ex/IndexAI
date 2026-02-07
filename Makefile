.PHONY: dev stop backend frontend worker beat migrate test

SHELL := /bin/bash
export PATH := /opt/homebrew/bin:/opt/homebrew/opt/postgresql@16/bin:$(PATH)

dev:
	./start-dev.sh

backend:
	source .venv/bin/activate && cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

worker:
	source .venv/bin/activate && cd backend && celery -A celery_app worker --loglevel=info --concurrency=2

beat:
	source .venv/bin/activate && cd backend && celery -A celery_app beat --loglevel=info

migrate:
	source .venv/bin/activate && cd backend && alembic upgrade head

migration:
	source .venv/bin/activate && cd backend && alembic revision --autogenerate -m "$(MSG)"

db-reset:
	dropdb indexing_service --if-exists && createdb indexing_service && psql indexing_service -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
	$(MAKE) migrate

stop:
	-lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	-lsof -ti:3000 | xargs kill -9 2>/dev/null || true
	-pkill -f "celery -A celery_app" 2>/dev/null || true
