"""Postgres checkpointer wiring for LangGraph."""

from functools import lru_cache
from typing import Any, cast

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from retail_agent.config import get_settings


@lru_cache(maxsize=1)
def get_checkpointer_pool() -> ConnectionPool[Connection[dict[str, Any]]]:
    """Return the cached psycopg pool used only by the LangGraph checkpointer."""

    return cast(
        ConnectionPool[Connection[dict[str, Any]]],
        ConnectionPool(
            conninfo=get_settings().db_uri,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            open=True,
        ),
    )


def build_postgres_saver(*, setup: bool = True) -> PostgresSaver:
    """Build a PostgresSaver over the cached native-psycopg pool."""

    saver = PostgresSaver(get_checkpointer_pool())
    if setup:
        saver.setup()
    return saver


def close_checkpointer_pool() -> None:
    """Close the cached checkpointer pool when a short-lived process is done."""

    if get_checkpointer_pool.cache_info().currsize == 0:
        return
    get_checkpointer_pool().close()
    get_checkpointer_pool.cache_clear()
