"""Tests for the DAG runner and the runtime quality gate."""
from __future__ import annotations

import pytest

from etl.quality import DataQualityError, run_quality_checks
from orchestration.dag import DAG, Task


# --- DAG engine ----------------------------------------------------------
def test_dag_runs_in_dependency_order():
    order: list[str] = []
    dag = DAG("t")
    dag.add(Task("a", lambda ctx: order.append("a")))
    dag.add(Task("b", lambda ctx: order.append("b"), depends_on=["a"]))
    dag.add(Task("c", lambda ctx: order.append("c"), depends_on=["b"]))
    dag.run()
    assert order == ["a", "b", "c"]


def test_dag_passes_context_between_tasks():
    dag = DAG("t")
    dag.add(Task("produce", lambda ctx: ctx.update(value=21)))
    dag.add(
        Task("double", lambda ctx: ctx.update(result=ctx["value"] * 2),
             depends_on=["produce"]),
    )
    ctx = dag.run()
    assert ctx["result"] == 42


def test_dag_detects_cycle():
    dag = DAG("t")
    dag.add(Task("a", lambda ctx: None, depends_on=["b"]))
    dag.add(Task("b", lambda ctx: None, depends_on=["a"]))
    with pytest.raises(ValueError, match="Cycle"):
        dag.run()


def test_dag_retries_then_succeeds():
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")

    dag = DAG("t")
    dag.add(Task("flaky", flaky, retries=1))
    dag.run()
    assert calls["n"] == 2


# --- Quality gate --------------------------------------------------------
def test_quality_gate_passes_on_valid_tables(star):
    run_quality_checks(star)  # should not raise


def test_quality_gate_fails_on_bad_review_score(star):
    bad = {k: v.copy() for k, v in star.items()}
    bad["dim_reviews"].loc[:, "review_score"] = 9  # out of 1-5 range
    with pytest.raises(DataQualityError):
        run_quality_checks(bad)
