"""Staging layer: clean each raw source 1:1 (no joins, no business modelling).

This mirrors the dbt convention of a `staging` schema: one cleaned table per
source, with consistent types, de-duplication and light normalisation. The
marts layer (star schema) is then built *from* staging, never from raw — so
cleaning rules live in exactly one place.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

_ORDER_DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def _stg_orders(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    for col in _ORDER_DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.drop_duplicates(subset="order_id")


def _stg_products(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    df = products.merge(translation, on="product_category_name", how="left")
    df["product_category"] = (
        df["product_category_name_english"]
        .fillna(df["product_category_name"])
        .fillna("unknown")
    )
    return df[["product_id", "product_category"]].drop_duplicates(subset="product_id")


def _stg_payments(payments: pd.DataFrame) -> pd.DataFrame:
    df = payments.copy()
    df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce")
    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"], errors="coerce"
    )
    df = df.drop_duplicates(subset=["order_id", "payment_sequential"])
    return df.dropna(subset=["order_id", "payment_sequential", "payment_value"])


def _stg_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    df = reviews.copy()
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    if "review_creation_date" in df.columns:
        df["review_creation_date"] = pd.to_datetime(
            df["review_creation_date"], errors="coerce"
        )
        df = df.sort_values("review_creation_date")
    df = df.dropna(subset=["review_score"]).drop_duplicates(
        subset="order_id", keep="last"
    )
    return df[["order_id", "review_score"]]


def _stg_geolocation(geo: pd.DataFrame) -> pd.DataFrame:
    return (
        geo.groupby("geolocation_zip_code_prefix")
        .agg(
            geolocation_lat=("geolocation_lat", "mean"),
            geolocation_lng=("geolocation_lng", "mean"),
            geolocation_state=("geolocation_state", "first"),
        )
        .reset_index()
    )


def build_staging(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Produce one cleaned staging table per source."""
    stg = {
        "stg_orders": _stg_orders(raw["orders"]),
        "stg_order_items": raw["order_items"].copy(),
        "stg_customers": raw["customers"].drop_duplicates(subset="customer_id"),
        "stg_products": _stg_products(raw["products"], raw["category_translation"]),
        "stg_sellers": raw["sellers"].drop_duplicates(subset="seller_id"),
        "stg_payments": _stg_payments(raw["payments"]),
        "stg_reviews": _stg_reviews(raw["reviews"]),
        "stg_geolocation": _stg_geolocation(raw["geolocation"]),
    }
    for name, df in stg.items():
        logger.info("Staged %-18s %7d rows", name, len(df))
    return stg
