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


def _clean_payments(payments: pd.DataFrame) -> pd.DataFrame:
    """Payments fact: one row per payment line of an order.

    An order can be split across several payment methods, so the grain is
    (order_id, payment_sequential). Values are coerced to numeric.
    """
    df = payments.copy()
    df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce")
    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"], errors="coerce"
    )
    df = df.drop_duplicates(subset=["order_id", "payment_sequential"])
    df = df.dropna(subset=["order_id", "payment_sequential", "payment_value"])
    return df


def _clean_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Reviews dimension: one row per order, keeping the latest review.

    Some orders received more than one review; we keep the most recent one
    so the dimension stays at one row per order (joinable to the fact table).
    """
    df = reviews.copy()
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    if "review_creation_date" in df.columns:
        df["review_creation_date"] = pd.to_datetime(
            df["review_creation_date"], errors="coerce"
        )
        df = df.sort_values("review_creation_date")
    # keep="last" -> the most recent review for each order.
    df = df.dropna(subset=["review_score"]).drop_duplicates(
        subset="order_id", keep="last"
    )
    return df[["order_id", "review_score"]]


def _clean_geolocation(geo: pd.DataFrame) -> pd.DataFrame:
    """Geolocation dimension: one row per zip-code prefix.

    The raw table has many noisy points per prefix; we collapse them to a
    single representative lat/lng (mean) with the dominant city/state.
    """
    df = geo.copy()
    agg = (
        df.groupby("geolocation_zip_code_prefix")
        .agg(
            geolocation_lat=("geolocation_lat", "mean"),
            geolocation_lng=("geolocation_lng", "mean"),
            geolocation_state=("geolocation_state", "first"),
        )
        .reset_index()
    )
    return agg


def build_star_schema(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Turn the dict of raw tables into cleaned dimension and fact tables.

    Returns a dict of table_name -> DataFrame ready to load.
    """
    orders = _clean_orders(raw["orders"])
    dim_products = _clean_products(raw["products"], raw["category_translation"])
    dim_customers = raw["customers"].drop_duplicates(subset="customer_id")
    dim_sellers = raw["sellers"].drop_duplicates(subset="seller_id")
    dim_reviews = _clean_reviews(raw["reviews"])
    dim_geolocation = _clean_geolocation(raw["geolocation"])
    fact_payments = _clean_payments(raw["payments"])

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

    # Enrich the fact with the order's review score (nullable: not every
    # order was reviewed). This lets us relate delivery performance to
    # customer satisfaction in a single table.
    fact = fact.merge(dim_reviews, on="order_id", how="left")

    tables = {
        "dim_customers": dim_customers,
        "dim_products": dim_products,
        "dim_sellers": dim_sellers,
        "dim_reviews": dim_reviews,
        "dim_geolocation": dim_geolocation,
        "fact_order_items": fact,
        "fact_payments": fact_payments,
    }
    for name, df in tables.items():
        logger.info("Transformed %-18s %7d rows", name, len(df))
    return tables
