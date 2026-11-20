"""Data-quality tests: the contract the pipeline guarantees downstream.

These check the three things that break analytics most often:
  1. integrity  - required keys are never null;
  2. consistency - no duplicate grain, derived values are correct;
  3. referential - every fact row points to a real dimension row.
"""
from __future__ import annotations

from etl.config import FACT_REQUIRED_COLUMNS


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
