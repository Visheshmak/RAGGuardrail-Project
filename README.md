# RAGGuard

Regression-Safe RAG Guardrails Evaluation Platform

## Project Overview

RAGGuard is a platform designed to evaluate Retrieval-Augmented Generation (RAG) systems, track guardrails, detect regressions, and manage release gating. This repository contains the project foundation.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, Celery
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **Infrastructure**: PostgreSQL, Redis, Qdrant, Docker

## Architecture

Please refer to [Architecture Documentation](docs/architecture.md) for detailed components mapping.

## Local Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 20+
- Python 3.12+

### Running the Application

1. Clone the repository
2. Copy the `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Start the application using Docker Compose:
   ```bash
   make build
   make up
   ```
4. Services will be available at:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Database Migrations

To apply database migrations:
```bash
make migrate
```

To create a new migration:
```bash
make makemigrations m="description"
```

## Testing

Run backend tests:
```bash
make test-backend
```
