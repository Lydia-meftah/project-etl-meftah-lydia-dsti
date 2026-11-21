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

## Architecture

The warehouse is built in layers, the dbt-style convention that keeps cleaning
and modelling separate:

```
raw CSVs ──▶ staging (1:1 cleaned) ──▶ marts (star schema) ──▶ quality gate ──▶ warehouse ──▶ dashboard
```

- **staging** (`etl/staging.py`) — one cleaned table per source, no joins.
- **marts** (`etl/marts.py`) — the dimensional model, built from staging only.
- **quality gate** (`etl/quality.py`) — the contract checked on the *real*
  tables at run time; a bad load is stopped before it reaches the warehouse.
- **orchestration** (`orchestration/`) — a dependency-aware DAG runs the whole
  thing (`extract → stage → marts → quality_gate → load`), with logging,
  timing and retries. It maps directly onto Airflow / Prefect.

## Project structure

```
olist-etl/
├── etl/
│   ├── config.py        # paths, source files, quality contract (single source of truth)
│   ├── extract.py       # load raw CSVs — no business logic
│   ├── staging.py       # 1:1 cleaned source tables (staging layer)
│   ├── marts.py         # dimensional model built from staging (marts layer)
│   ├── transform.py     # staging + marts entry point
│   ├── quality.py       # runtime data-quality gate
│   ├── load.py          # idempotent write to the SQLite warehouse
│   └── pipeline.py      # simple linear run
├── orchestration/
│   ├── dag.py           # minimal dependency-aware DAG engine
│   └── flow.py          # the Olist pipeline as an orchestrated DAG
├── dashboard/
│   └── build_dashboard.py  # renders a static KPI dashboard (HTML) from the warehouse
├── tests/               # 26 tests: data quality, staging, DAG engine, quality gate
├── analytics/kpis.sql   # example KPI queries on the star schema
├── Makefile             # make install / run / orchestrate / dashboard / test
└── requirements.txt
```

## Quickstart

```bash
make install                 # install dependencies
# download the Olist CSVs from Kaggle into data/raw/
make orchestrate             # run the pipeline through the DAG (with quality gate)
make dashboard               # build dashboard/dashboard.html from the warehouse
make test                    # run the test suite (26 tests)
sqlite3 data/processed/olist.db < analytics/kpis.sql   # see the KPIs in SQL
```

`make run` runs the same steps as a simple linear script; `make orchestrate`
runs them through the DAG with the quality gate — use either.

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

Python · pandas · SQL (SQLite) · pytest · Make · Chart.js (dashboard) ·
staging/marts layering · DAG orchestration
