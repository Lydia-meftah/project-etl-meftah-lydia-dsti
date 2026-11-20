"""Data-quality tests: the contract the pipeline guarantees downstream.

These check the three things that break analytics most often:
  1. integrity  - required keys are never null;
  2. consistency - no duplicate grain, derived values are correct;
  3. referential - every fact row points to a real dimension row.
"""
from __future__ import annotations

from etl.config import (
    FACT_REQUIRED_COLUMNS,
    PAYMENTS_REQUIRED_COLUMNS,
    REVIEW_SCORE_MAX,
    REVIEW_SCORE_MIN,
)


# --- 1. Integrity --------------------------------------------------------
def test_required_columns_have_no_nulls(star):
    fact = star["fact_order_items"]
    for col in FACT_REQUIRED_COLUMNS:
        assert fact[col].notna().all(), f"Null found in required column '{col}'"


# --- 2. Consistency ------------------------------------------------------
def test_fact_grain_is_unique(star):
    """One row per (order_id, order_item_id): the declared grain holds."""
    fact = star["fact_order_items"]
    assert not fact.duplicated(subset=["order_id", "order_item_id"]).any()


def test_duplicate_orders_were_removed(star):
    """The duplicated 'o2' order must not inflate the fact table."""
    fact = star["fact_order_items"]
    assert (fact["order_id"] == "o2").sum() == 1


def test_delivery_days_is_correct(star):
    """o1 was purchased on Jan 1 and delivered Jan 5 -> 4 days."""
    fact = star["fact_order_items"]
    o1 = fact[fact["order_id"] == "o1"].iloc[0]
    assert o1["delivery_days"] == 4


def test_late_flag_is_correct(star):
    """o2 was delivered after its estimated date -> is_late is True."""
    fact = star["fact_order_items"]
    assert fact[fact["order_id"] == "o2"]["is_late"].iloc[0]
    assert not fact[fact["order_id"] == "o1"]["is_late"].iloc[0]


def test_total_item_value_equals_price_plus_freight(star):
    fact = star["fact_order_items"]
    assert (fact["total_item_value"] == fact["price"] + fact["freight_value"]).all()


def test_missing_category_defaults_to_unknown(star):
    """Product p2 had no category; it must fall back, never become null."""
    dim = star["dim_products"]
    assert dim["product_category"].notna().all()


# --- 3. Referential integrity -------------------------------------------
def test_every_fact_product_exists_in_dimension(star):
    fact, dim = star["fact_order_items"], star["dim_products"]
    assert set(fact["product_id"]).issubset(set(dim["product_id"]))


def test_every_fact_customer_exists_in_dimension(star):
    fact, dim = star["fact_order_items"], star["dim_customers"]
    assert set(fact["customer_id"]).issubset(set(dim["customer_id"]))


# --- 4. Payments fact ----------------------------------------------------
def test_payments_required_columns_have_no_nulls(star):
    pay = star["fact_payments"]
    for col in PAYMENTS_REQUIRED_COLUMNS:
        assert pay[col].notna().all(), f"Null in required payment column '{col}'"


def test_payments_grain_is_unique(star):
    """One row per (order_id, payment_sequential)."""
    pay = star["fact_payments"]
    assert not pay.duplicated(subset=["order_id", "payment_sequential"]).any()


def test_payment_values_are_non_negative(star):
    pay = star["fact_payments"]
    assert (pay["payment_value"] >= 0).all()


# --- 5. Reviews dimension ------------------------------------------------
def test_reviews_are_unique_per_order(star):
    dim = star["dim_reviews"]
    assert not dim.duplicated(subset="order_id").any()


def test_latest_review_is_kept(star):
    """Order o2 was reviewed twice; the most recent score (4) must win."""
    dim = star["dim_reviews"]
    assert dim.loc[dim["order_id"] == "o2", "review_score"].iloc[0] == 4


def test_review_scores_are_in_valid_range(star):
    dim = star["dim_reviews"]
    assert dim["review_score"].between(REVIEW_SCORE_MIN, REVIEW_SCORE_MAX).all()


# --- 6. Geolocation dimension -------------------------------------------
def test_geolocation_is_unique_per_zip_prefix(star):
    dim = star["dim_geolocation"]
    assert not dim.duplicated(subset="geolocation_zip_code_prefix").any()
