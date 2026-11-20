"""Transform step: clean the raw tables and build a star schema.

Design choice — grain of the fact table
----------------------------------------
The fact table is `fact_order_items`: one row per *item* within an order
(an order can contain several items). This is the natural grain for an
e-commerce analytics model because revenue, freight and the product/seller
involved are all defined at the item level, not the order level.

Around it sit conformed dimensions (customers, products, sellers, orders).
This is a classic Kimball star schema: simple joins, fast aggregations.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Order timestamp columns that must be parsed from text to real datetimes.
_ORDER_DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def _clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Parse dates and drop exact duplicate orders."""
    df = orders.copy()
    for col in _ORDER_DATE_COLS:
        if col in df.columns:
            # errors="coerce": unparseable dates become NaT rather than crashing.
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.drop_duplicates(subset="order_id")
    return df


def _clean_products(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    """Translate category names to English and fill missing categories."""
    df = products.merge(translation, on="product_category_name", how="left")
    # Keep a single, analysis-friendly English category column.
    df["product_category"] = (
        df["product_category_name_english"]
        .fillna(df["product_category_name"])
        .fillna("unknown")
    )
    return df[["product_id", "product_category"]].drop_duplicates(subset="product_id")


def build_star_schema(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Turn the dict of raw tables into cleaned dimension and fact tables.

    Returns a dict of table_name -> DataFrame ready to load.
    """
    orders = _clean_orders(raw["orders"])
    dim_products = _clean_products(raw["products"], raw["category_translation"])
    dim_customers = raw["customers"].drop_duplicates(subset="customer_id")
    dim_sellers = raw["sellers"].drop_duplicates(subset="seller_id")

    # --- Build the fact table -------------------------------------------
    items = raw["order_items"].copy()

    # Attach the customer and the key order timestamps from the orders table.
    order_cols = [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    fact = items.merge(orders[order_cols], on="order_id", how="inner")

    # --- Derived business metrics (this is where raw data gains meaning) --
    # Actual delivery time, in days, from purchase to customer receipt.
    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]
    ).dt.days

    # Was the order delivered later than the date promised to the customer?
    fact["is_late"] = (
        fact["order_delivered_customer_date"] > fact["order_estimated_delivery_date"]
    )
    # Undelivered orders have NaT -> the comparison is NA; treat as "not late".
    fact["is_late"] = fact["is_late"].fillna(False)

    # Total value a customer paid for the line = product price + freight.
    fact["total_item_value"] = fact["price"] + fact["freight_value"]

    # Guarantee the key columns carry no nulls (contract for downstream use).
    fact = fact.dropna(subset=["order_id", "product_id", "seller_id", "customer_id"])

    tables = {
        "dim_customers": dim_customers,
        "dim_products": dim_products,
        "dim_sellers": dim_sellers,
        "fact_order_items": fact,
    }
    for name, df in tables.items():
        logger.info("Transformed %-18s %7d rows", name, len(df))
    return tables
