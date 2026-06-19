.PHONY: install lint test full-check run db-up db-down db-migrate eval ingest-golden

install:
	@uv sync --extra dev

lint:
	.venv/bin/ruff check src $$( [ -d tests ] && echo tests )
	.venv/bin/ruff format --check src $$( [ -d tests ] && echo tests )
	.venv/bin/mypy src

test:
	.venv/bin/pytest

full-check: lint test

run:
	.venv/bin/python -m retail_agent

db-up:
	docker compose up -d db
	docker compose exec -T db pg_isready -U postgres -d postgres

db-down:
	docker compose down

# Run after db-up; the Golden-bucket schema is owned by Alembic, not init.sql.
db-migrate:
	.venv/bin/alembic upgrade head

eval:
	.venv/bin/python -m retail_agent.eval

ingest-golden:
	.venv/bin/python -m retail_agent.ingest_golden
