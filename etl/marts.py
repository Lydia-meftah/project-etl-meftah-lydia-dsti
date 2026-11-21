"""Marts layer: build the dimensional model (star schema) from staging.

Marts consume *staging* tables only. This layer does the modelling —
joins, derived business metrics, and the fact/dimension split — but no raw
cleaning (that already happened in staging).
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_marts(stg: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Build dimension and fact tables from the staging tables."""
    orders = stg["stg_orders"]
    dim_reviews = stg["stg_reviews"]

    # --- Fact: order items -------------------------------------------------
    order_cols = [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    fact = stg["stg_order_items"].merge(orders[order_cols], on="order_id", how="inner")

    # Derived business metrics.
    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]
    ).dt.days
    fact["is_late"] = (
        fact["order_delivered_customer_date"] > fact["order_estimated_delivery_date"]
    ).fillna(False)
    fact["total_item_value"] = fact["price"] + fact["freight_value"]

    fact = fact.dropna(subset=["order_id", "product_id", "seller_id", "customer_id"])
    # Attach the order's review score (nullable: not every order was reviewed).
    fact = fact.merge(dim_reviews, on="order_id", how="left")

    tables = {
        "dim_customers": stg["stg_customers"],
        "dim_products": stg["stg_products"],
        "dim_sellers": stg["stg_sellers"],
        "dim_reviews": dim_reviews,
        "dim_geolocation": stg["stg_geolocation"],
        "fact_order_items": fact,
        "fact_payments": stg["stg_payments"],
    }
    for name, df in tables.items():
        logger.info("Modelled %-18s %7d rows", name, len(df))
    return tables
