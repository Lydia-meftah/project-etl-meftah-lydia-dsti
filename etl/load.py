"""Load step: write the cleaned tables to a SQLite warehouse.

SQLite is used as a lightweight stand-in for a real warehouse (BigQuery,
Postgres, Snowflake). The loading contract is the same: idempotent writes
(re-running replaces the table), so the pipeline can be run repeatedly
without creating duplicates.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from etl.config import DB_PATH

logger = logging.getLogger(__name__)


def load_tables(tables: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> Path:
    """Write each DataFrame to its own table in the SQLite database.

    ``if_exists="replace"`` makes the load idempotent: running the pipeline
    twice yields the same database, never duplicated rows.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
            logger.info("Loaded %-18s -> %s (%d rows)", name, db_path.name, len(df))

    return db_path
