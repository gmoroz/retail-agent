"""Read-only BigQuery data access."""

import os
from functools import lru_cache

import google.api_core.exceptions as gax_exceptions
import pandas as pd
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict

from retail_agent.config import get_settings
from retail_agent.const import (
    BIGQUERY_JOB_TIMEOUT_MS,
    MAX_BIGQUERY_BYTES_BILLED,
    THELOOK_DATASET,
    THELOOK_PROJECT,
    THELOOK_TABLES,
)
from retail_agent.exceptions import BigQueryExecutionError


class ColumnSchema(BaseModel):
    """One column of an allowlist table, for DB-structure answers."""

    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str


@lru_cache(maxsize=1)
def get_client() -> bigquery.Client:
    """Return the cached BigQuery client for the configured project."""

    settings = get_settings()
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
    return bigquery.Client(project=settings.google_cloud_project)


def dry_run_bytes(sql: str) -> int:
    """Return BigQuery's byte estimate for ``sql`` without executing it."""

    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    client = get_client()
    try:
        job = client.query(sql, job_config=job_config)
    except gax_exceptions.GoogleAPIError as exc:
        raise BigQueryExecutionError(f"dry run failed: {exc}") from exc
    return int(job.total_bytes_processed or 0)


def run_query(sql: str) -> pd.DataFrame:
    """Execute ``sql`` and return the result as a DataFrame."""

    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=MAX_BIGQUERY_BYTES_BILLED,
        use_query_cache=False,
        job_timeout_ms=BIGQUERY_JOB_TIMEOUT_MS,
    )
    client = get_client()
    try:
        job = client.query(sql, job_config=job_config)
        rows = job.result(timeout=BIGQUERY_JOB_TIMEOUT_MS / 1000)
        return rows.to_dataframe(create_bqstorage_client=False)
    except (gax_exceptions.GoogleAPIError, TimeoutError) as exc:
        raise BigQueryExecutionError(f"query execution failed: {exc}") from exc


def introspect_schema() -> dict[str, list[ColumnSchema]]:
    """Return ``{dataset.table: [columns]}`` for every allowlist table."""

    client = get_client()
    schema: dict[str, list[ColumnSchema]] = {}
    for table_name in sorted(THELOOK_TABLES):
        ds_table = f"{THELOOK_DATASET}.{table_name}"
        ref = f"{THELOOK_PROJECT}.{ds_table}"
        try:
            table_schema = client.get_table(ref)
        except gax_exceptions.GoogleAPIError as exc:
            raise BigQueryExecutionError(f"schema introspection failed for {ref}: {exc}") from exc
        schema[ds_table] = [ColumnSchema(name=field.name, data_type=field.field_type) for field in table_schema.schema]
    return schema
