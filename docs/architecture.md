# retail-agent High-Level Design

`retail-agent` is a synchronous CLI analytics assistant over the public BigQuery
dataset `bigquery-public-data.thelook_ecommerce`. A manager asks a natural-language
question, the LangGraph workflow generates read-only GoogleSQL, validates and runs
it with cost controls, masks PII before report generation, and returns a concise
business answer.

The prototype implements the selected code layers: Safety and PII masking,
Resilience, Observability, and Quality Assurance. It also partially implements
Hybrid Intelligence through Golden-bucket few-shot retrieval. High-Stakes
Oversight, Continuous Improvement, and advanced Persona Management are documented
as production design extensions where they are not part of the prototype.

## Architecture diagrams

### Component view

```mermaid
flowchart LR
    Manager[Retail manager] --> CLI[CLI chat loop]
    CLI --> Graph[LangGraph StateGraph]

    subgraph Agent[Agent workflow]
        Guard[guard]
        Retrieve[retrieve_golden]
        Generate[generate_sql]
        Validate[validate_sql]
        Run[run_sql masks rows before state update]
        SelfCorrect[self_correct]
        Report[generate_report]
        Scrub[scrub_report]
        Finalize[finalize]
        Refuse[refuse]
        NoData[no_data_report]
        CostRefusal[cost_refusal]
        Failure[failure_response]
    end

    Graph --> Guard
    Guard --> Retrieve
    Guard --> Refuse
    Guard --> Failure
    Retrieve --> Generate
    Generate --> Validate
    Generate --> Failure
    Validate --> Run
    Validate --> SelfCorrect
    Run --> Report
    Run --> SelfCorrect
    Run --> NoData
    Run --> CostRefusal
    Run --> Failure
    SelfCorrect --> Generate
    Report --> Scrub
    Report --> Failure
    Refuse --> Finalize
    NoData --> Finalize
    CostRefusal --> Finalize
    Failure --> Finalize
    Scrub --> Finalize

    Graph --> Services[services]
    Graph --> Repositories
    Services --> LLMFactory[LLM factory]
    Services --> Safety[Safety and PII]
    Services --> SQLValidation[SQL validation]
    Services --> Observability[Trace collector]
    Services --> Reporting[Reporting]

    Services --> Repositories[repositories]
    Repositories --> BQ[(BigQuery thelook ecommerce read-only)]
    Repositories --> PG[(Postgres + pgvector)]
    Repositories --> OR[OpenRouter]

    PG --> Checkpointer[LangGraph checkpointer tables]
    PG --> Golden[golden_trios + HNSW vector index]
    OR --> Chat[Chat models and judge]
    OR --> Embeddings[baai/bge-m3 embeddings]

    Eval[Offline A/B eval harness] --> Graph
    Eval --> BQ
    Eval --> OR
```

### Request sequence

```mermaid
sequenceDiagram
    actor User as Manager
    participant CLI as CLI
    participant Graph as LangGraph StateGraph
    participant Safety as Safety service
    participant OR as OpenRouter
    participant PG as Postgres + pgvector
    participant SQL as SQL validation
    participant BQ as BigQuery
    participant Report as Reporting service
    participant Trace as TraceCollector

    User->>CLI: Natural-language question
    CLI->>Graph: invoke(question, thread_id)
    Graph->>Safety: guard question
    Graph->>Safety: mask_question(email regex)
    Graph->>OR: classify masked question
    alt blocked, off-topic, or injection
        Graph->>Trace: finalize(blocked)
        Graph-->>CLI: refusal
    else allowed
        Graph->>OR: embed masked question
        OR-->>Graph: 1024-d vector
        Graph->>PG: retrieve top-k Golden Trios by cosine distance
        PG-->>Graph: few-shot examples
        Graph->>BQ: introspect allowlist table schema
        Graph->>OR: generate SQL from masked question
        Graph->>SQL: parse, one statement, read-only deny-list, table subset, PII output guard
        alt invalid SQL and retry budget remains
            Graph->>Graph: self_correct count + feedback
            Graph->>OR: regenerate SQL
        else valid SQL
            Graph->>BQ: dry run byte estimate
            alt estimate exceeds cap
                Graph->>Trace: finalize(cost_exceeded)
                Graph-->>CLI: cost refusal
            else within cap
                Graph->>BQ: execute with maximum_bytes_billed and timeout
                alt BigQuery execution error and retry budget remains
                    Graph->>Graph: self_correct count + feedback
                    Graph->>OR: regenerate SQL
                else empty result
                    Graph->>Trace: finalize(no_data)
                    Graph-->>CLI: no-data response
                else rows returned
                    Graph->>Safety: mask rows before checkpoint state update
                    Graph->>Report: generate manager report from masked rows
                    Report->>OR: report LLM call with masked question
                    Graph->>Safety: scrub_report email safety net
                    Graph->>Trace: finalize(ok)
                    Graph-->>CLI: scrubbed report
                end
            end
        end
    end
```

## Implemented code anchors

The HLD below is grounded in the current code, not only in the plan:

| Area | Implementation anchors |
|---|---|
| Graph nodes and routing | `src/retail_agent/agent/graph.py:149`, `src/retail_agent/agent/graph.py:293`, `src/retail_agent/agent/graph.py:367` |
| Serializable graph state and outcomes | `src/retail_agent/agent/state.py:8`, `src/retail_agent/agent/state.py:19` |
| SQL prompts and self-correction prompt | `src/retail_agent/agent/prompts.py:8`, `src/retail_agent/agent/prompts.py:71` |
| Env-driven settings and sync DB URL split | `src/retail_agent/config.py:18`, `src/retail_agent/config.py:92` |
| Table allowlist, PII columns, model slugs | `src/retail_agent/const.py:19`, `src/retail_agent/const.py:28`, `src/retail_agent/const.py:53` |
| SQL AST validation | `src/retail_agent/services/sql_validation.py:41` |
| Guard and PII masking | `src/retail_agent/services/safety.py:185`, `src/retail_agent/services/safety.py:282` |
| Report generation from masked rows | `src/retail_agent/services/reporting.py:40` |
| Trace collection and JSON logging | `src/retail_agent/services/observability.py:155`, `src/retail_agent/services/observability.py:241` |
| LLM factory | `src/retail_agent/services/llm.py:32` |
| BigQuery dry run, execution, schema introspection | `src/retail_agent/repositories/bigquery.py:35`, `src/retail_agent/repositories/bigquery.py:47`, `src/retail_agent/repositories/bigquery.py:67` |
| Service-layer BigQuery cost guard | `src/retail_agent/services/query_execution.py:27` |
| Golden retrieval orchestration | `src/retail_agent/services/retrieval.py:22` |
| OpenRouter embeddings | `src/retail_agent/repositories/embeddings.py:19`, `src/retail_agent/repositories/embeddings.py:46` |
| Golden bucket retrieval | `src/retail_agent/repositories/golden_bucket.py:41`, `src/retail_agent/repositories/golden_bucket.py:63` |
| LangGraph Postgres checkpointer | `src/retail_agent/repositories/postgres.py:14`, `src/retail_agent/repositories/postgres.py:28` |
| Golden Trio ORM model and Alembic schema | `src/retail_agent/models.py:20`, `alembic/versions/0001_init_golden_bucket.py:19` |
| CLI resilience boundary | `src/retail_agent/cli.py:59`, `src/retail_agent/cli.py:86` |
| Eval runner and ranking | `src/retail_agent/evaluation/runner.py:31`, `src/retail_agent/evaluation/ranking.py:37` |

Implementation note: `AgentDependencies` now injects cohesive services for
Golden retrieval, schema loading, and query execution, while repositories remain
thin I/O modules. The BigQuery cost decision lives in
`QueryExecutionService`, not in `repositories/bigquery.py`.

## Technical choices

### Synchronous CLI and LangGraph StateGraph

The project is a synchronous CLI, not a web service. There is no HTTP API, FastAPI
router, event loop, or async database layer. The CLI only parses input, manages
`thread_id`, prints output, and delegates to a compiled LangGraph graph
(`src/retail_agent/cli.py:59`, `src/retail_agent/cli.py:86`). Business logic lives
in services and graph nodes; data access lives in repositories.

LangGraph `StateGraph` is used instead of a prebuilt agent because the workflow has
explicit safety gates, SQL validation, bounded self-correction, cost refusal,
no-data handling, PII ordering, and trace finalization. Those branches are visible
in the graph wiring (`src/retail_agent/agent/graph.py:367`) and correspond to
ADR-024.

### Postgres + pgvector as one state store

Postgres is the single state store for two different concerns:

- LangGraph checkpointer tables, created by `PostgresSaver.setup()` at runtime over
  a native psycopg pool (`src/retail_agent/repositories/postgres.py:28`).
- Golden bucket rows in `golden_trios`, managed by SQLAlchemy and Alembic
  (`src/retail_agent/models.py:20`, `alembic/versions/0001_init_golden_bucket.py:19`).

This follows ADR-002 and ADR-019. It avoids a split SQLite plus vector-store setup
and keeps chat history, graph state, and few-shot knowledge in one production-shaped
database. The schema uses pgvector `Vector(1024)` and an HNSW index with
`vector_cosine_ops` (`alembic/versions/0001_init_golden_bucket.py:36`), matching
ADR-012.

### BigQuery read-only analytics source

BigQuery is the only analytics data source and is treated as read-only. The code
enforces read-only behavior before execution with sqlglot AST validation, then uses
BigQuery dry runs and server-side caps:

- `validate_read_only_sql` requires exactly one statement, rejects DML/DDL nodes,
  and requires every referenced table to be in the allowlist
  (`src/retail_agent/services/sql_validation.py:41`).
- `QueryExecutionService` asks BigQuery for a byte estimate and rejects
  over-budget SQL before execution (`src/retail_agent/services/query_execution.py:27`).
- `run_query` executes validated SQL with `maximum_bytes_billed` plus
  `job_timeout_ms` as BigQuery-side request limits
  (`src/retail_agent/repositories/bigquery.py:47`).

The production IAM posture is a read-only BigQuery service account with data-viewer
and job-runner permissions only. The prototype keeps credentials out of the repo
and loads them from ADC or `GOOGLE_APPLICATION_CREDENTIALS`
(`src/retail_agent/config.py:38`).

### OpenRouter LLMs, embeddings, and judge

One OpenAI-compatible path is used for chat models, A/B candidates, the judge, and
embeddings:

- The default chat factory reads `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`
  for provider-agnostic dev or production endpoints (`src/retail_agent/services/llm.py:63`).
- A/B and judge calls use OpenRouter with explicit model slugs
  (`src/retail_agent/services/llm.py:46`).
- Embeddings use OpenRouter `baai/bge-m3`, and the repository validates the returned
  vector dimension against 1024 (`src/retail_agent/repositories/embeddings.py:32`).

The A/B set is `deepseek/deepseek-v4-flash`, `qwen/qwen3.7-plus`,
`moonshotai/kimi-k2`, and `z-ai/glm-5.2`; the judge is
`google/gemini-3.5-flash` (`src/retail_agent/const.py:53`,
`src/retail_agent/const.py:60`). ADR-016 selected these from the OpenRouter catalog
and Tinybird SQL Generation Benchmark as a text-to-SQL focused mix of price and
quality. The completed 4x20 eval pins `deepseek/deepseek-v4-flash` as the default:
correctness tied at 0.800 across deepseek, qwen and glm; glm's 0.635 quality and
deepseek's 0.633 quality fall inside the 0.05 LLM-judge noise band, so PR-005
falls through to cost and latency.

### SQL validation with sqlglot

sqlglot is used because the target dialect is BigQuery GoogleSQL, not Postgres.
The validator calls `sqlglot.parse(..., dialect="bigquery")` so multi-statement
SQL is visible and rejected, then uses a read-only deny-list instead of requiring
the top-level expression to be `Select`. That permits valid top-level `UNION` and
CTE queries while still rejecting DML and DDL (`src/retail_agent/services/sql_validation.py:51`).
ADR-009 and ADR-018 document this choice.

### Alembic + SQLAlchemy

Golden-bucket schema is owned by Alembic migrations, not a Docker `init.sql`.
`Base.metadata` is the migration target (`src/retail_agent/models.py:16`), and
the migration creates the `vector` extension, table, and HNSW index
(`alembic/versions/0001_init_golden_bucket.py:19`). `DB_URI` stays in native
`postgresql://` form for psycopg and is converted to `postgresql+psycopg://` only
for SQLAlchemy consumers (`src/retail_agent/config.py:92`), as recorded in ADR-021.

## Data flow

1. The CLI starts logging, compiles the graph once, creates a `thread_id`, and
   invokes the graph for each user question (`src/retail_agent/cli.py:59`).
2. `guard` creates a per-run `TraceCollector`, stores the human message, and runs
   the safety guard. Rule hits block prompt injection and destructive SQL phrases
   without an LLM call; remaining questions are classified by an LLM
   (`src/retail_agent/agent/graph.py:144`, `src/retail_agent/services/safety.py:185`).
   Schema metadata questions are allowed deterministically and return the formatted
   allowlist schema without embeddings, SQL generation, or query execution.
3. `guard` stores an email-masked question before external question-bearing model
   calls. `retrieve_golden` reuses that masking before embeddings, calls
   OpenRouter `baai/bge-m3`, and retrieves top-k Golden Trios by pgvector cosine
   distance (`src/retail_agent/agent/graph.py:178`,
   `src/retail_agent/repositories/golden_bucket.py:63`).
4. `generate_sql` loads the allowlist table schema from BigQuery, builds the SQL
   prompt with the masked question, schema and few-shot examples, and invokes the chat model
   (`src/retail_agent/agent/graph.py:190`,
   `src/retail_agent/agent/prompts.py:71`).
5. `validate_sql` enforces the sqlglot read-only contract and rejects output
   projections derived from raw PII columns, including aliases and functions
   (`src/retail_agent/agent/graph.py:229`).
6. `run_sql` delegates dry-run cost checking and masked execution to
   `QueryExecutionService`, then stores only masked rows in a
   checkpoint-serializable form
   (`src/retail_agent/agent/graph.py:242`, `src/retail_agent/agent/graph.py:133`).
7. Invalid SQL and BigQuery execution errors route to `self_correct`, which adds
   feedback to the next SQL prompt until `MAX_SELF_CORRECT_ITERATIONS` is reached
   (`src/retail_agent/agent/graph.py:239`, `src/retail_agent/agent/graph.py:343`).
8. Empty valid results route to `no_data_report`; they are not self-corrected
   (`src/retail_agent/agent/graph.py:353`).
9. Non-empty masked rows pass to `generate_report`. The report LLM receives the
   masked question and masked data (`src/retail_agent/agent/graph.py:267`,
   `src/retail_agent/services/reporting.py:40`).
10. `scrub_report` applies the email safety net after the LLM, then `finalize`
    emits the trace and adds the AI message to state (`src/retail_agent/agent/graph.py:283`,
    `src/retail_agent/agent/graph.py:133`).

## Error handling and fallback strategies

- Input guard failures produce a refusal and route to `finalize` with `blocked`
  outcome (`src/retail_agent/agent/graph.py:166`).
- LLM failures in guard, SQL generation, or reporting are caught in graph nodes and
  return a neutral failure response instead of crashing the CLI
  (`src/retail_agent/agent/graph.py:161`, `src/retail_agent/agent/graph.py:211`,
  `src/retail_agent/agent/graph.py:283`).
- Golden retrieval failure is degraded to no few-shot examples; the graph still
  tries to answer from schema and the SQL prompt (`src/retail_agent/agent/graph.py:187`).
- SQL validation errors and BigQuery execution errors enter a bounded
  self-correction loop (`src/retail_agent/agent/graph.py:326`,
  `src/retail_agent/agent/graph.py:337`).
- BigQuery cost overrun is a terminal cost refusal, not a self-correction attempt
  (`src/retail_agent/agent/graph.py:335`).
- Empty results are a terminal no-data answer, not an error
  (`src/retail_agent/agent/graph.py:339`).
- Chat models and embeddings use fixed retry counts and request timeouts from
  `const.py` (`src/retail_agent/services/llm.py:58`,
  `src/retail_agent/repositories/embeddings.py:24`).
- The eval harness adds explicit retry handling for rate-limit shaped failures
  (`src/retail_agent/evaluation/runner.py:157`, `src/retail_agent/evaluation/scoring.py:75`).
- The CLI has the outer resilience boundary: it logs domain or unexpected failures
  and keeps the chat loop alive (`src/retail_agent/cli.py:86`).

## Observability

Each graph invocation has a `TraceCollector`. It records every chat-model call,
latency, prompt and completion tokens, total tokens, and OpenRouter charged cost
when the provider returns it (`src/retail_agent/services/observability.py:126`).
At graph finalization it adds outcome, total latency, BigQuery bytes,
self-correction iterations, and the last error (`src/retail_agent/services/observability.py:241`).
`configure_logging` emits JSON logs for machine parsing
(`src/retail_agent/services/observability.py:77`).

Conversation recovery and multi-turn continuity come from LangGraph checkpointer
state keyed by the CLI `thread_id` (`src/retail_agent/cli.py:35`,
`src/retail_agent/repositories/postgres.py:28`).

## Setup and run

Prerequisites:

- Python 3.13.12.
- `uv`.
- Docker for Postgres + pgvector.
- Google Cloud credentials with BigQuery access to public datasets.
- OpenRouter API key for embeddings, A/B models, and judge.

Install and configure:

```bash
uv venv .venv --python 3.13.12
make install
cp .env.example .env
```

Fill `.env`:

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=<openrouter-or-compatible-key>
LLM_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_API_KEY=<openrouter-key-for-embeddings-eval-judge>
GOOGLE_CLOUD_PROJECT=<your-gcp-project-for-billing>
DB_URI=postgresql://postgres:postgres@localhost:5432/postgres
```

If not using a service-account file, authenticate with ADC outside the repo:

```bash
gcloud auth application-default login
```

Start and migrate Postgres:

```bash
make db-up
make db-migrate
make ingest-golden
```

Run the chat:

```bash
make run
```

The live OpenRouter/deepseek AC1 transcript is committed in
[`docs/example_run.md`](example_run.md). It covers customer behavior, product
performance, time-based revenue, and deterministic schema introspection.

Run checks and eval:

```bash
make full-check
make eval
```

`make eval` executes the offline A/B harness. The full four-model by twenty-question
run requires valid OpenRouter and BigQuery credentials. `python -m retail_agent.eval
--rerank-from eval/results.json` rebuilds `eval/results.md` from saved case rows
without new LLM or BigQuery calls.

## Requirement coverage

### 1. Hybrid Intelligence

Status: implemented in prototype, with a design extension for ongoing learning.

The Golden bucket stores Trios: question, SQL, report, and embedding
(`src/retail_agent/models.py:20`). `make ingest-golden` loads seed Trios from
`eval/seed_trios.json` through `ingest_seed_trios`
(`src/retail_agent/evaluation/io.py:67`, `src/retail_agent/ingest_golden.py:19`).
At query time, the graph masks emails in the question, embeds the masked question
with OpenRouter `baai/bge-m3`, retrieves top-k similar Trios by pgvector cosine
distance, and injects them into the SQL prompt (`src/retail_agent/agent/graph.py:181`,
`src/retail_agent/agent/prompts.py:51`).

Production learning loop: successful or human-approved interactions become new
candidate Trios, are reviewed for SQL correctness and PII safety, embedded, and
inserted into the Golden bucket. The prototype has the ingestion path and retrieval
path; automatic promotion from live conversations is design-only.

### 2. Safety and PII Masking

Status: implemented in prototype.

Input safety combines deterministic regex blocking for prompt injection and
destructive SQL phrases with an LLM classifier for intent and off-topic questions
(`src/retail_agent/services/safety.py:42`, `src/retail_agent/services/safety.py:185`).
SQL safety is enforced by sqlglot AST validation and BigQuery caps
(`src/retail_agent/services/sql_validation.py:41`,
`src/retail_agent/services/query_execution.py:27`).

PII masking is ordered so raw result PII does not reach either checkpoint state
or the report LLM: `run_sql masks rows -> generate_report -> scrub_report`.
`mask_data` replaces known `users` PII columns and applies the shared email regex
to string cells (`src/retail_agent/services/safety.py:268`). The PII set is
limited to individual identifiers and precise location fields: `email`,
`first_name`, `last_name`, `street_address`, `postal_code`, `latitude`,
`longitude`, and `user_geom`; `city`, `state`, and `country` remain analytical
dimensions. The SQL validator rejects output expressions that reference these
PII source columns, even through aliases or functions, and asks the model to use
`user_id` instead (`src/retail_agent/services/sql_validation.py:51`).
`scrub_report` is an email-only safety net after the report LLM
(`src/retail_agent/services/safety.py:90`).
`mask_question` pre-masks emails before all external question-bearing model calls:
guard classification, OpenRouter embeddings, SQL generation, and report generation
(`src/retail_agent/services/safety.py:84`).

Production extension: Presidio or another NER layer can be added for names,
phones, and unstructured text if the dataset or user questions expand beyond the
fixed thelook schema.

### 3. High-Stakes Oversight

Status: design-only, not implemented in the prototype.

The production design adds a Saved Reports library in Postgres. Destructive
commands such as "delete reports mentioning refunds" or "delete today's reports"
would be parsed into candidate report IDs, previewed to the user, and paused with
LangGraph `interrupt()`. The user confirms through `Command(resume=...)`; only then
does the graph delete reports owned by the current user. The UX remains chat-native:
the assistant asks for confirmation inside the conversation instead of redirecting
to an admin flow.

The current code has no Saved Reports model or destructive operation path, so this
requirement is intentionally HLD-only.

### 4. Continuous Improvement

Status: design-only, with prototype building blocks.

System-level improvement is the Golden-bucket learning loop described under Hybrid
Intelligence: approved successful interactions are promoted to Trios and retrieved
as few-shot context in future runs. The prototype includes seed ingestion and
retrieval, but not automatic approval workflows.

User-level improvement adds a preferences table keyed by user or manager persona.
Examples: Manager A prefers compact tables; Manager B prefers short bullet
summaries. The graph would load preferences before report generation and pass them
into the report prompt. The current prototype has prompt constants and a
thread-level checkpointer, but no persisted user preferences.

### 5. Resilience and Graceful Error Handling

Status: implemented in prototype.

The graph degrades retrieval failure to an empty few-shot list
(`src/retail_agent/agent/graph.py:187`), retries SQL generation through bounded
self-correction on validation and execution errors (`src/retail_agent/agent/graph.py:326`,
`src/retail_agent/agent/graph.py:337`), treats empty valid results as no-data
(`src/retail_agent/agent/graph.py:339`), and refuses over-budget queries before
execution (`src/retail_agent/agent/graph.py:247`). LLM and embedding clients carry
configured retry counts and timeouts (`src/retail_agent/services/llm.py:58`,
`src/retail_agent/repositories/embeddings.py:24`). The CLI catches failures at the
interaction boundary and keeps the process alive (`src/retail_agent/cli.py:86`).

### 6. Quality Assurance

Status: implemented in prototype.

The offline A/B harness reuses the production graph per model slug instead of a
separate SQL-only shortcut (`src/retail_agent/evaluation/runner.py:157`). It loads a seed
set and a physically separate holdout set, then asserts they do not overlap
(`src/retail_agent/evaluation/io.py:54`). Generated SQL is executed and compared
against reference SQL with canonicalized rows (`src/retail_agent/evaluation/scoring.py:41`).
Report quality is judged separately by the fixed judge model
(`src/retail_agent/evaluation/scoring.py:75`). Ranking is deterministic:
correctness descending, 0.05-banded quality descending, mean cost ascending,
mean latency ascending, model name tie-break (`src/retail_agent/evaluation/ranking.py:37`).
The quality band is the PR-005 guardrail against treating tiny LLM-judge
differences as signal.

| Model | Correctness | Quality | Mean cost | Mean latency |
|---|---:|---:|---:|---:|
| `deepseek/deepseek-v4-flash` | 0.800 | 0.633 | 0.000342 | 24.67s |
| `z-ai/glm-5.2` | 0.800 | 0.635 | 0.006724 | 44.87s |
| `qwen/qwen3.7-plus` | 0.800 | 0.620 | 0.005896 | 97.48s |
| `moonshotai/kimi-k2` | 0.550 | 0.585 | 0.001255 | 29.61s |

The pinned default is `deepseek/deepseek-v4-flash` because it ties on correctness,
lands in the same quality band as glm, and is materially cheaper and faster.

The winning correctness score is 0.800 (16/20) under a strict subset-by-value
metric on open-ended analytics questions. Some failed cases are interpretation or
result-shape differences from the reference SQL rather than agent crashes: the QA
run recorded stable graph outcomes with no crashes, while judged report quality
averaged about 0.63.

The eval set contains twenty holdout questions across customer behavior, product
performance, time-based analysis, comparisons, repeat customers, and DB structure
(`eval/golden_set.json:1`).

### 7. Observability

Status: implemented in prototype.

Each run returns and logs a trace with `trace_id`, outcome, latency, tokens, cost
when available, LLM call count, BigQuery bytes, self-correction iterations, and
error (`src/retail_agent/services/observability.py:105`,
`src/retail_agent/services/observability.py:241`). Logs are JSON formatted
(`src/retail_agent/services/observability.py:59`). Conversation and state replay
are supported by LangGraph checkpointer storage in Postgres
(`src/retail_agent/repositories/postgres.py:28`).

### 8. Agility and Persona Management

Status: partially implemented in prototype, production extension documented.

Prompt text is isolated as module constants instead of being embedded in CLI or
repository code. SQL prompts live in `agent/prompts.py`
(`src/retail_agent/agent/prompts.py:8`), the report persona lives in
`services/reporting.py` (`src/retail_agent/services/reporting.py:15`), and the
guard classifier prompt lives in `services/safety.py`
(`src/retail_agent/services/safety.py:162`). This makes persona and wording changes
localized.

Production extension: move persona prompts and user preference templates into a
versioned prompt store or operations-managed config table. Non-developers could
edit approved personas without redeploying code, while the graph loads the active
prompt version at startup or per request.

## Prototype boundary

Implemented in code:

- CLI chat loop with multi-turn `thread_id`.
- LangGraph workflow with guard, retrieval, SQL generation, validation, execution,
  self-correction, PII masking, report generation, report scrubbing, and trace
  finalization.
- BigQuery read-only validation and cost controls.
- Postgres checkpointer plus pgvector Golden bucket.
- OpenRouter chat, embeddings, A/B eval models, and judge path.
- Offline A/B eval harness and deterministic ranking.

Design-only:

- Saved Reports library and destructive-operation HITL confirmation.
- Automatic promotion of live interactions into the Golden bucket.
- Persisted per-user reporting preferences.
- External prompt/persona store editable by non-developers without redeploy.
- Presidio or equivalent NER for broader unstructured PII coverage.
