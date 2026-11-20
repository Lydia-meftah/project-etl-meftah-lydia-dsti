# Olist ETL — Data Engineering Pipeline

A production-style **ETL pipeline** in Python/pandas that turns the raw
[Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
into a clean **star schema** ready for analytics, with automated data-quality tests.

**Author:** Lydia Meftah — MSc Data Engineer / Applied AI (DSTI)

---

## Why this project

Raw transactional data is spread across several CSVs with inconsistent types,
duplicates, missing values and Portuguese labels. This pipeline applies the
core data-engineering steps — **Extract → Transform → Load** — to produce a
dimensional model that analysts and BI tools can query with simple joins, and
it guarantees that quality through tests.

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  EXTRACT │ ──▶ │  TRANSFORM  │ ──▶ │     LOAD     │ ──▶ │   ANALYTICS   │
│ raw CSVs │     │ clean +     │     │  SQLite      │     │  SQL KPIs /   │
│          │     │ star schema │     │  warehouse   │     │  BI dashboard │
└──────────┘     └─────────────┘     └──────────────┘     └───────────────┘
```

## Data model (fact constellation)

Two fact tables share conformed dimensions — a Kimball **fact constellation**
(a star schema extended with a second fact). `fact_order_items` is at the
**order-item grain**; `fact_payments` is at the **payment grain** (an order
can be paid with several methods).

```
   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │ dim_customers│     │  dim_reviews │     │ dim_geolocation│
   └──────┬───────┘     └──────┬───────┘     └──────────────┘
          │                    │
┌──────────────┐   ┌───────────┴──────┐   ┌──────────────┐
│ dim_products │───│ fact_order_items │───│  dim_sellers │
└──────────────┘   │  (grain: item)   │   └──────────────┘
                   │  price, freight, │
                   │  delivery_days,  │
                   │  is_late,        │
                   │  review_score    │
                   └──────────────────┘
                   ┌──────────────────┐
                   │   fact_payments  │  grain: one payment line per order
                   │  type, value,    │
                   │  installments    │
                   └──────────────────┘
```

Tables produced:
- **fact_order_items** — revenue grain, enriched with `delivery_days`,
  `is_late` (delivered after the promised date), `total_item_value`
  (price + freight) and the order's `review_score`.
- **fact_payments** — one row per payment line: method, value, installments.
- **dim_customers / dim_products / dim_sellers** — conformed dimensions.
- **dim_reviews** — one row per order (latest review kept), 1–5 star score.
- **dim_geolocation** — one row per zip-code prefix (mean lat/lng).

## Project structure

```
olist-etl/
├── etl/
│   ├── config.py      # paths, source files, quality contract (single source of truth)
│   ├── extract.py     # load raw CSVs — no business logic
│   ├── transform.py   # clean + build the star schema (the core logic)
│   ├── load.py        # idempotent write to the SQLite warehouse
│   └── pipeline.py    # orchestrates Extract → Transform → Load
├── tests/
│   └── test_data_quality.py  # integrity, consistency & referential checks
├── analytics/
│   └── kpis.sql       # example KPI queries on the star schema
├── Makefile           # make install / run / test
└── requirements.txt
```

## Quickstart

```bash
make install                 # install dependencies
# download the Olist CSVs from Kaggle into data/raw/
make run                     # Extract → Transform → Load  ->  data/processed/olist.db
make test                    # run the data-quality test suite
sqlite3 data/processed/olist.db < analytics/kpis.sql   # see the KPIs
```

## Data quality

The pipeline is covered by tests that encode the contract it guarantees
downstream (run with `make test`):

- **Integrity** — required keys are never null (order items and payments).
- **Consistency** — each declared grain is unique (order-item and payment),
  duplicates are removed, review scores stay within 1–5, payment values are
  non-negative, and each derived metric is correct.
- **Referential integrity** — every fact row points to an existing dimension row.

Tests run on a small synthetic fixture, so they execute in milliseconds and
need no dataset download — suitable for CI.

## Design choices

- **Separation of concerns** — extract does no cleaning; all business rules
  live in `transform.py`, so each step is independently testable.
- **Idempotent load** — re-running replaces tables, never duplicates rows.
- **Config in one place** — paths and the quality contract live in `config.py`,
  so the pipeline can be pointed at another environment by editing one file.
- **SQLite as a stand-in warehouse** — the same contract maps directly onto
  BigQuery / Postgres / Snowflake.

## Tech stack

Python · pandas · SQL (SQLite) · pytest · Make
