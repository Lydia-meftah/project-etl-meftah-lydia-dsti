"""Shared pytest fixtures.

A tiny synthetic version of the Olist tables is built here so the
data-quality tests run in milliseconds and need no Kaggle download. The
synthetic data is crafted to exercise the transform logic: a multi-item
order, a late delivery, a missing product category and a duplicate order.
"""
from __future__ import annotations

import pandas as pd
import pytest

from etl.transform import build_star_schema


@pytest.fixture
def raw_sample() -> dict[str, pd.DataFrame]:
    """Minimal but representative raw tables, mirroring the real schema."""
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o2"],  # o2 duplicated on purpose
            "customer_id": ["c1", "c2", "c2"],
            "order_status": ["delivered", "delivered", "delivered"],
            "order_purchase_timestamp": [
                "2018-01-01 10:00:00",
                "2018-02-01 10:00:00",
                "2018-02-01 10:00:00",
            ],
            "order_approved_at": [
                "2018-01-01 11:00:00",
                "2018-02-01 11:00:00",
                "2018-02-01 11:00:00",
            ],
            "order_delivered_carrier_date": [None, None, None],
            "order_delivered_customer_date": [
                "2018-01-05 10:00:00",  # on time (4 days)
                "2018-02-20 10:00:00",  # late
                "2018-02-20 10:00:00",
            ],
            "order_estimated_delivery_date": [
                "2018-01-10 10:00:00",
                "2018-02-10 10:00:00",  # promised earlier than delivered -> late
                "2018-02-10 10:00:00",
            ],
        }
    )
    order_items = pd.DataFrame(
        {
            "order_id": ["o1", "o1", "o2"],  # o1 has two items
            "order_item_id": [1, 2, 1],
            "product_id": ["p1", "p2", "p1"],
            "seller_id": ["s1", "s1", "s2"],
            "price": [100.0, 50.0, 200.0],
            "freight_value": [10.0, 5.0, 20.0],
        }
    )
    customers = pd.DataFrame(
        {"customer_id": ["c1", "c2"], "customer_state": ["SP", "RJ"]}
    )
    products = pd.DataFrame(
        {
            "product_id": ["p1", "p2"],
            "product_category_name": ["cama_mesa_banho", None],  # p2 has no category
        }
    )
    sellers = pd.DataFrame(
        {"seller_id": ["s1", "s2"], "seller_state": ["SP", "MG"]}
    )
    translation = pd.DataFrame(
        {
            "product_category_name": ["cama_mesa_banho"],
            "product_category_name_english": ["bed_bath_table"],
        }
    )
    payments = pd.DataFrame(
        {
            "order_id": ["o1", "o1", "o2"],  # o1 split across two methods
            "payment_sequential": [1, 2, 1],
            "payment_type": ["credit_card", "voucher", "boleto"],
            "payment_installments": [3, 1, 1],
            "payment_value": [150.0, 15.0, 220.0],
        }
    )
    reviews = pd.DataFrame(
        {
            "review_id": ["r1", "r2", "r2b"],
            "order_id": ["o1", "o2", "o2"],  # o2 reviewed twice
            "review_score": [5, 2, 4],
            "review_creation_date": [
                "2018-01-06",
                "2018-02-21",
                "2018-02-25",  # latest -> this one (score 4) is kept
            ],
        }
    )
    geolocation = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": [1000, 1000, 2000],
            "geolocation_lat": [-23.5, -23.6, -22.9],
            "geolocation_lng": [-46.6, -46.7, -43.2],
            "geolocation_state": ["SP", "SP", "RJ"],
        }
    )
    return {
        "orders": orders,
        "order_items": order_items,
        "customers": customers,
        "products": products,
        "sellers": sellers,
        "category_translation": translation,
        "payments": payments,
        "reviews": reviews,
        "geolocation": geolocation,
    }


@pytest.fixture
def star(raw_sample) -> dict[str, pd.DataFrame]:
    """The star schema built from the synthetic sample."""
    return build_star_schema(raw_sample)
