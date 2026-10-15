.PHONY: up down build test-backend build-frontend logs migrate makemigrations shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up --build -d

logs:
	docker compose logs -f

test-backend:
	docker compose exec backend pytest

build-frontend:
	docker compose exec frontend npm run build

makemigrations:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

migrate:
	docker compose exec backend alembic upgrade head

shell:
	docker compose exec backend /bin/bash
