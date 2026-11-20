"""Pipeline orchestration: wire Extract -> Transform -> Load together.

Run as a module:  python -m etl.pipeline
or via the Makefile: make run
"""
from __future__ import annotations

import logging

from etl.extract import extract_all
from etl.load import load_tables
from etl.transform import build_star_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("olist-etl")


def run() -> None:
    """Execute the full ETL pipeline end to end."""
    logger.info("=== Olist ETL pipeline started ===")

    raw = extract_all()                 # Extract
    tables = build_star_schema(raw)     # Transform
    db_path = load_tables(tables)       # Load

    logger.info("=== Pipeline finished. Warehouse ready at %s ===", db_path)


if __name__ == "__main__":
    run()
