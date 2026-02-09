# IndexAI

SEO indexation service that automates URL submission to search engines and tracks indexing status.

## Features

- **Multi-method indexing** — Google Indexing API, IndexNow, sitemap pings, social signals, backlink pings
- **Google Search Console integration** — import sitemaps, verify indexing via GSC Inspection API
- **Service account rotation** — round-robin across multiple Google service accounts
- **Verification system** — automated checks with GSC + Custom Search API fallback
- **Credit system** — per-URL billing with automatic refunds on failure
- **Real-time dashboard** — daily stats, indexing speed, method success rates
- **Project management** — group URLs by project, filter/search/paginate, CSV export

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| Task queue | Celery + Redis |
| Database | PostgreSQL |
| Frontend | React, Vite, TailwindCSS |
| Auth | JWT (access + refresh tokens) |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis

### Setup

```bash
# Clone
git clone https://github.com/a2ex/IndexAI.git
cd IndexAI

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Database
createdb indexing_service
psql indexing_service -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

# Environment
cp .env.example .env
# Edit .env with your credentials

# Migrations
make migrate
```

### Run

```bash
# Start all services (backend, frontend, celery workers, beat)
make dev

# Or individually:
make backend        # FastAPI on :8000
make frontend       # Vite on :3000
make worker         # Celery indexing worker
make worker-verify  # Celery verification worker (solo pool)
make beat           # Celery beat scheduler
```

### Other Commands

```bash
make stop              # Kill all services
make migrate           # Run migrations
make migration MSG="description"  # Create new migration
make db-reset          # Drop + recreate DB
```

## Docker

```bash
docker build -t indexai .
docker run -p 8000:8000 --env-file .env indexai
```

## Environment Variables

See [`.env.example`](.env.example) for all available configuration options.

Key variables:
- `DATABASE_URL` / `DATABASE_URL_SYNC` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `SECRET_KEY` — JWT signing key
- `GOOGLE_CUSTOM_SEARCH_API_KEY` / `GOOGLE_CSE_ID` — for indexing verification
- `CREDENTIALS_DIR` — path to Google service account JSON files

## Architecture

```
backend/
  app/
    api/           # FastAPI routes
    models/        # SQLAlchemy models
    schemas/       # Pydantic schemas
    services/      # Business logic
      indexing/    # Submission methods
      verification/# Index checking
    tasks/         # Celery tasks
frontend/
  src/
    pages/         # Route pages
    components/    # Shared components
    api/           # API client
```

Two Celery worker pools:
- **`celery` queue** (prefork) — indexing tasks
- **`verification` queue** (solo pool) — async verification tasks

## License

Private project.
