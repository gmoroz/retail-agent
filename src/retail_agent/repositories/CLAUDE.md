# repositories/

Data access only.

- Postgres + pgvector Golden bucket (ingest / retrieve top-k).
- BigQuery read-only execution (dry run, capped run, schema introspection).
- OpenRouter embeddings client (baai/bge-m3).

Called by services; never by the CLI. No business logic: a repository performs the
I/O its caller requests and returns plain data for the service to interpret.
