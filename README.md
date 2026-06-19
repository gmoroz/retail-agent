# retail-agent

CLI chat agent for retail analytics. It answers natural-language questions over
the public BigQuery dataset `bigquery-public-data.thelook_ecommerce`, using
LangGraph for orchestration, OpenRouter chat with the pinned SLA-aware default
`deepseek/deepseek-v4-flash`, and OpenRouter embeddings (`baai/bge-m3`).

See [docs/architecture.md](docs/architecture.md) for the high-level design,
Mermaid diagrams, requirement coverage and production extensions.

## Requirements

- Python 3.13.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker (for the Postgres + pgvector container)
- A Google Cloud project with BigQuery access
- An OpenRouter API key (LLM, embeddings, eval)

## Setup

```bash
uv venv .venv --python 3.13.12
make install
cp .env.example .env   # then fill in the values
make db-up             # start Postgres + pgvector
make db-migrate        # apply Alembic schema migrations
make ingest-golden     # seed the Golden bucket few-shot examples
```

Alternatively, with plain pip (installs the project and its pinned deps from `pyproject.toml`):

```bash
pip install .
cp .env.example .env   # then fill in the values
docker compose up -d db
alembic upgrade head
python -m retail_agent.ingest_golden
python -m retail_agent
```

For plain-pip users, the manual equivalents of the Makefile targets are
`alembic upgrade head` for `make db-migrate`, `python -m retail_agent` for
`make run`, and `python -m retail_agent.eval` for `make eval`. The Makefile targets
assume the uv-managed `.venv`.

Configure the environment in `.env`:

- `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` -- any OpenAI-compatible chat
  completions endpoint. The committed default is OpenRouter with
  `deepseek/deepseek-v4-flash`; use the same OpenRouter key for `LLM_API_KEY`.
- `OPENROUTER_API_KEY` -- OpenRouter key for embeddings, A/B eval and the judge.
- `GOOGLE_CLOUD_PROJECT` -- GCP project used for BigQuery billing.
- `GOOGLE_APPLICATION_CREDENTIALS` -- optional path to a service-account JSON
  (otherwise ADC via `gcloud auth application-default login`).
- `DB_URI` -- Postgres connection string (matches `make db-up`).

## Run

```bash
make run
```

A real OpenRouter/deepseek run is captured in
[docs/example_run.md](docs/example_run.md).

## A/B selection

The human-readable 4x20 eval ranking is [eval/results.md](eval/results.md). Full
per-case details, including generated SQL and judge reasons, are stored in
[eval/results.json](eval/results.json). Ranking uses correctness first, then
report-quality bands with a 0.05 LLM-judge noise floor, then mean cost and mean
latency. That PR-005 rule keeps `qwen/qwen3.7-plus` as the accuracy leader, but
the deployed CLI default must fit the interactive latency SLA (`<=45s` mean
latency). `qwen` is one holdout question more correct than `deepseek`, but is
about 4.4x slower and 17x more expensive on mean cost, so
`deepseek/deepseek-v4-flash` remains the pinned default.

| Model | Correctness | Quality | Mean cost | Mean latency |
|---|---:|---:|---:|---:|
| `qwen/qwen3.7-plus` | 0.750 | 0.670 | 0.005827 | 95.34s |
| `deepseek/deepseek-v4-flash` | 0.700 | 0.635 | 0.000340 | 21.64s |
| `z-ai/glm-5.2` | 0.650 | 0.605 | 0.005878 | 27.77s |
| `moonshotai/kimi-k2` | 0.450 | 0.532 | 0.001223 | 24.16s |

## Development

```bash
make lint        # ruff check + ruff format --check + mypy (strict)
make test        # pytest
make full-check  # lint + test (final verification)
make db-up       # start Postgres + pgvector
make db-down     # stop Postgres
make db-migrate  # apply Alembic migrations
make eval        # run the offline A/B eval harness
```
