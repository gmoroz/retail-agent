# retail-agent

CLI chat agent for retail analytics on LangGraph + BigQuery + OpenRouter.
Data source: public dataset `bigquery-public-data.thelook_ecommerce` (read-only).

## Stack
- Python 3.13.12 (pinned in `.python-version` and `requires-python`).
- LangGraph 1.x + LangChain 1.x (V1) -- agent orchestration.
- langchain-openai -- single generic OpenAI-compatible LLM factory (OpenRouter for
  A/B + judge + embeddings; the same path serves dev via a different base_url/key).
- google-cloud-bigquery + db-dtypes + pandas -- data access, results as DataFrame.
- pydantic + pydantic-settings -- models and env-driven configuration.
- sqlglot -- read-only SQL AST validation (BigQuery dialect).
- Postgres + pgvector -- single store for LangGraph checkpointer (chat history) and
  the Golden bucket (embeddings). Brought up via `docker compose`.
- SQLAlchemy 2.x (sync) + Alembic -- Golden-bucket ORM model and versioned schema
  migrations (no raw `init.sql`). The checkpointer tables are created by
  `PostgresSaver.setup()` at runtime, not by migrations.
- Tooling: uv, ruff, mypy (strict), pytest.

## Layered architecture (no HTTP API)
This is a CLI, so there is no API layer. Layers are:

- `cli.py` / `__main__.py` -- I/O only: parse input, print output, delegate.
  No business logic, no direct repository calls, no DB/BQ access.
- `services/` -- business logic (SQL validation, LLM factory, safety/PII masking,
  observability, reporting). Returns domain models, never raw ORM/DF rows.
- `repositories/` -- data access only (Postgres+pgvector Golden bucket, BigQuery
  read-only execution, embeddings client). Called by services, never by CLI.
- `agent/` -- LangGraph graph (nodes, state, checkpointer wiring, prompts).

Business logic lives in `services/` and `agent/`; I/O lives in `repositories/`;
`cli/` only parses and prints. Each module ships its own `CLAUDE.md`.

## Database schema
- `src/retail_agent/models.py` -- SQLAlchemy 2.x sync Declarative `Base` +
  `GoldenTrio` (pgvector `Vector(1024)`). `Base.metadata` is the Alembic target.
- Alembic (`alembic/`, `alembic.ini`) owns the schema: the first migration creates
  the `vector` extension, the `golden_trios` table and its HNSW index. Applied via
  `make db-migrate` (`alembic upgrade head`) after `make db-up`. No `init.sql`.
- LangGraph `PostgresSaver` creates its own checkpointer tables via `.setup()` at
  runtime; they are intentionally not migrated.

## Configuration
- Only via environment variables (`pydantic-settings`). No hardcoded secrets.
- Template is `.env.example`. The local `.env` is gitignored.
- Variables: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (provider-agnostic
  OpenAI-compatible endpoint), `OPENROUTER_API_KEY` (A/B + judge + embeddings),
  `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS` (optional -> ADC),
  `DB_URI`.

## Environment and dependencies
- Only `uv` + `.venv`. `pip` / system python are forbidden for development.
- Versions are pinned strictly with `==` in `pyproject.toml` as the single source of truth.
- Install: `make install` (`uv sync --extra dev`); plain pip users run `pip install .`.

## Code style
- ASCII only in code (`->`, `>=`). Unicode arrows/operators are forbidden.
- SUPER HARD RULE: ALL docstrings, comments, README, HLD, commit messages, and any
  text in this repo are ENGLISH ONLY (reviewers know English only). A docstring is
  required on every public function.
- Code is comment-free by default. Comments are ONLY for non-obvious "why" (never
  "what"). Forbidden: banner separators (`# --- ... ---`, `# ===`), label comments
  above field groups, and a `#` comment that duplicates an adjacent
  `Field(description=...)` or docstring. Group with a blank line instead.
- Forbidden in production code: `print()` (exception: CLI entry point, per-file
  ignore), bare `except Exception` (BLE001 -- catch specific exceptions, e.g.
  `sqlglot.errors.ParseError`), `TODO`/`FIXME`/`HACK`, empty `except`, hardcoded
  config. Catch specific exceptions, not bare `Exception`.
- Domain naming. Forbidden names: `data`, `result`, `item`, single letters (except
  `i`/`j`/`k` in short loops, `_`). Repeats -> constants; codes/types -> enums.
- No blocking calls inside async code (this project is synchronous CLI + sync
  PostgresSaver + sync BigQuery client, so there is no event loop).

## Commands
- `make install` -- install dependencies (`uv sync --extra dev`).
- `make lint` -- ruff check + ruff format --check + mypy strict.
- `make test` -- pytest.
- `make full-check` -- lint + test. The ONLY final verification before delivery.
- `make run` -- launch the CLI (`python -m retail_agent`).
- `make db-up` / `make db-down` -- start/stop the Postgres+pgvector container.
- `make db-migrate` -- apply Alembic migrations (`alembic upgrade head`).
- `make eval` -- run the A/B eval harness.
- `make ingest-golden` -- ingest few-shot seed Trios into the Golden bucket.
