"""The Olist pipeline expressed as an orchestrated DAG.

Task graph:
    extract -> stage -> marts -> quality_gate -> load

Run:  python -m orchestration.flow   (or: make orchestrate)
"""
from __future__ import annotations

import logging

from etl.extract import extract_all
from etl.load import load_tables
from etl.marts import build_marts
from etl.quality import run_quality_checks
from etl.staging import build_staging
from orchestration.dag import DAG, Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


# --- Task functions: each reads/writes the shared context ----------------
def task_extract(ctx: dict) -> None:
    ctx["raw"] = extract_all()


def task_stage(ctx: dict) -> None:
    ctx["staging"] = build_staging(ctx["raw"])


def task_marts(ctx: dict) -> None:
    ctx["tables"] = build_marts(ctx["staging"])


def task_quality(ctx: dict) -> None:
    # Quality gate: raises and stops the DAG if the contract is violated.
    run_quality_checks(ctx["tables"])


def task_load(ctx: dict) -> None:
    ctx["db_path"] = load_tables(ctx["tables"])


def build_dag() -> DAG:
    dag = DAG("olist_etl")
    dag.add(Task("extract", task_extract))
    dag.add(Task("stage", task_stage, depends_on=["extract"]))
    dag.add(Task("marts", task_marts, depends_on=["stage"]))
    # Retry the quality gate once in case of a transient issue.
    dag.add(Task("quality_gate", task_quality, depends_on=["marts"], retries=1))
    dag.add(Task("load", task_load, depends_on=["quality_gate"]))
    return dag


def run() -> None:
    ctx = build_dag().run()
    logging.getLogger("orchestration").info("Warehouse ready at %s", ctx["db_path"])


if __name__ == "__main__":
    run()
