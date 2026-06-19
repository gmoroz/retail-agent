# services/

Business logic for the retail agent.

- SQL validation (read-only AST), the LLM factory, safety / PII masking,
  observability and reporting.
- Returns domain models, never raw ORM rows or DataFrames.
- Calls repositories for I/O; never touches BigQuery, Postgres or OpenRouter
  directly.
- No HTTP layer. Consumed by the agent graph and the CLI.

Do not put I/O code or CLI parsing here.
