"""Central configuration for the ETL pipeline.

Keeping paths and source-file names in one module means the rest of the
code never hard-codes a path, which makes the pipeline easy to point at a
different environment (local, CI, cloud bucket) by changing one file.
"""
from __future__ import annotations

from pathlib import Path

# Project root = parent of the `etl/` package directory.
ROOT_DIR = Path(__file__).resolve().parent.parent

# Where the raw Kaggle CSVs live, and where processed outputs are written.
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# Target SQLite database (the "warehouse" for this project).
DB_PATH = PROCESSED_DIR / "olist.db"

# Logical name -> raw CSV file name, as published on Kaggle.
# Only these tables are needed to build the star schema below.
SOURCE_FILES: dict[str, str] = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Columns that must never be null in the cleaned fact table. Used by the
# data-quality tests as the contract the pipeline guarantees downstream.
FACT_REQUIRED_COLUMNS: list[str] = [
    "order_id",
    "order_item_id",
    "product_id",
    "seller_id",
    "customer_id",
    "price",
]
