"""Tests for the staging layer (1:1 cleaned sources)."""
from __future__ import annotations

from etl.staging import build_staging


def test_staging_produces_all_tables(raw_sample):
    stg = build_staging(raw_sample)
    expected = {
        "stg_orders",
        "stg_order_items",
        "stg_customers",
        "stg_products",
        "stg_sellers",
        "stg_payments",
        "stg_reviews",
        "stg_geolocation",
    }
    assert expected.issubset(stg.keys())


def test_staging_orders_deduplicated(raw_sample):
    stg = build_staging(raw_sample)
    assert not stg["stg_orders"].duplicated(subset="order_id").any()


def test_staging_payments_grain_unique(raw_sample):
    stg = build_staging(raw_sample)
    pay = stg["stg_payments"]
    assert not pay.duplicated(subset=["order_id", "payment_sequential"]).any()


def test_staging_geolocation_one_row_per_prefix(raw_sample):
    stg = build_staging(raw_sample)
    geo = stg["stg_geolocation"]
    assert not geo.duplicated(subset="geolocation_zip_code_prefix").any()
