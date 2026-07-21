# 🛍️ E-Commerce Competitor Price Monitor & Dashboard



## Overview

A production-grade data engineering project that demonstrates:

- **ETL Pipeline** — Extract product data from REST APIs, transform with cleaning/normalization, load into a relational database
- **MySQL JSON Data Type** — Store unstructured product attributes (sizes, colors, specs, brand) alongside structured pricing data
- **Advanced SQL** — Window functions (LAG, LEAD, DENSE_RANK), CTEs, INSERT ON DUPLICATE KEY UPDATE, JSON_EXTRACT, JSON_TABLE
- **Price Tracking** — Historical price monitoring with automated alerts for significant price drops, increases, and stock changes
- **Interactive Dashboard** — Streamlit-powered data visualization with Plotly charts

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Data Sources | [FakeStoreAPI](https://fakestoreapi.com), [DummyJSON](https://dummyjson.com) |
| Database | SQLite (dev) / MySQL (production) |
| Visualization | Streamlit + Plotly |
| Testing | pytest |

## Quick Start

### 1. Install Dependencies

```bash
cd ecommerce-price-monitor
pip install -r requirements.txt
```

### 2. Run the Pipeline

```bash
# Live mode — scrapes from real APIs (no API key needed!)
python run_pipeline.py

# Seed mode — uses local sample data (no network needed)
python run_pipeline.py --seed

# Single source only
python run_pipeline.py --source FakeStore
```

### 3. Launch the Dashboard

```bash
streamlit run dashboard/app.py
```

### 4. Run Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
ecommerce-price-monitor/
├── config.py                 # Central configuration
├── run_pipeline.py           # CLI entry point
├── requirements.txt          # Dependencies
│
├── src/
│   ├── database.py           # DB connection + schema management
│   ├── transform.py          # Data normalization + JSON building
│   ├── load.py               # Upsert logic + alert generation
│   ├── pipeline.py           # ETL orchestrator
│   ├── mysql_adapter.py      # MySQL-specific adapter (PyMySQL)
│   └── scrapers/
│       ├── base_scraper.py   # Abstract base with retry logic
│       ├── fakestore_scraper.py
│       └── dummyjson_scraper.py
│
├── sql/                      # MySQL-compatible SQL showcases
│   ├── schema.sql            # Full relational schema with JSON
│   ├── json_queries.sql      # JSON_EXTRACT, JSON_TABLE demos
│   ├── upsert_queries.sql    # ON DUPLICATE KEY UPDATE patterns
│   ├── analytics.sql         # Window functions + CTEs
│   └── views_and_indexes.sql # Views + generated column indexes
│
├── dashboard/
│   ├── app.py                # Streamlit dashboard
│   └── components.py         # Reusable Plotly components
│
├── data/
│   ├── seed_products.json    # Demo data
│   └── price_monitor.db      # Generated SQLite DB
│
└── tests/
    ├── test_scrapers.py
    ├── test_transform.py
    └── test_load.py
```

## Database Schema

```
competitors ──┐
              ├── products (with JSON attributes) ──── price_history
categories ───┘                                    └── price_alerts
                                                   └── scrape_runs
```

### Key SQL Features Demonstrated

- **JSON Column**: `attributes JSON` for flexible product metadata
- **JSON Functions**: `JSON_EXTRACT`, `JSON_TABLE`, `JSON_MERGE_PATCH`, `->>` operator
- **Upserts**: `INSERT ... ON DUPLICATE KEY UPDATE` with JSON merging
- **Window Functions**: `LAG()`, `LEAD()`, `DENSE_RANK()`, `ROW_NUMBER()`, `NTILE()`
- **CTEs**: Multi-level aggregations, recursive queries
- **Views & Indexes**: Generated columns from JSON, composite indexes

## MySQL Connection (Optional)

For production MySQL, create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your MySQL credentials
DB_MODE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=price_monitor
```

## License

MIT
# ecommerce-price-monitor
