"""Runtime data-quality gate.

The pytest suite validates the logic on synthetic fixtures. This module runs
the *same* contract against the real built tables at pipeline time, so a bad
load is caught before it reaches the warehouse. The orchestration DAG runs
this as a gate between "build marts" and "load".
"""
from __future__ import annotations

import logging

import pandas as pd

from etl.config import (
    FACT_REQUIRED_COLUMNS,
    PAYMENTS_REQUIRED_COLUMNS,
    REVIEW_SCORE_MAX,
    REVIEW_SCORE_MIN,
)

logger = logging.getLogger(__name__)


class DataQualityError(AssertionError):
    """Raised when a built table violates the quality contract."""


def _check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def run_quality_checks(tables: dict[str, pd.DataFrame]) -> None:
    """Assert the contract on the real tables; raise if any check fails."""
    failures: list[str] = []

    fact = tables["fact_order_items"]
    for col in FACT_REQUIRED_COLUMNS:
        _check(fact[col].notna().all(), f"fact_order_items.{col} has nulls", failures)
    _check(
        not fact.duplicated(subset=["order_id", "order_item_id"]).any(),
        "fact_order_items grain not unique",
        failures,
    )

    pay = tables["fact_payments"]
    for col in PAYMENTS_REQUIRED_COLUMNS:
        _check(pay[col].notna().all(), f"fact_payments.{col} has nulls", failures)
    _check((pay["payment_value"] >= 0).all(), "negative payment_value", failures)

    rev = tables["dim_reviews"]
    _check(
        rev["review_score"].between(REVIEW_SCORE_MIN, REVIEW_SCORE_MAX).all(),
        "review_score out of 1-5 range",
        failures,
    )

    # Referential integrity: facts must point to existing dimensions.
    _check(
        set(fact["product_id"]).issubset(set(tables["dim_products"]["product_id"])),
        "fact_order_items references missing product",
        failures,
    )

    if failures:
        raise DataQualityError("Data-quality gate failed: " + "; ".join(failures))

    logger.info("Data-quality gate passed (%d tables checked)", len(tables))
