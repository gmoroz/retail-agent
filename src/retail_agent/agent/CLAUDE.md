# agent/

LangGraph orchestration.

- State, graph nodes, the checkpointer wiring and prompts.
- Nodes call services for business logic: SQL validation, safety, reporting and
  observability.
- Nodes wire repository functions through `AgentDependencies` for data access:
  BigQuery, embeddings and Golden-bucket retrieval.
- Keep business logic outside node composition; the graph is the dependency
  injection orchestrator.

The graph is synchronous; the checkpointer is PostgresSaver backed by Postgres.
