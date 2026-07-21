"""
Database connection manager and schema initialization.
Supports SQLite (local dev) and MySQL (production).
"""
import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)

# ── SQLite JSON compatibility ─────────────────────────────────────────────
# SQLite doesn't have native JSON functions pre-3.38, so we store JSON as TEXT
# and handle extraction in Python. The schema mirrors MySQL's structure.

SQLITE_SCHEMA = """
-- Competitor sources (FakeStore, DummyJSON, etc.)
CREATE TABLE IF NOT EXISTS competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Products with JSON attributes column
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category_id INTEGER,
    attributes TEXT,  -- JSON stored as TEXT in SQLite (JSON type in MySQL)
    source_competitor_id INTEGER,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (source_competitor_id) REFERENCES competitors(id)
);

-- Price history for tracking over time
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    competitor_id INTEGER NOT NULL,
    price REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    in_stock INTEGER DEFAULT 1,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (competitor_id) REFERENCES competitors(id),
    UNIQUE(product_id, competitor_id, scraped_at)
);

-- Automated price alerts
CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    alert_type TEXT CHECK(alert_type IN ('price_drop', 'price_increase', 'back_in_stock', 'out_of_stock')),
    old_price REAL,
    new_price REAL,
    pct_change REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Pipeline run tracking
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    products_scraped INTEGER DEFAULT 0,
    status TEXT CHECK(status IN ('running', 'completed', 'failed')),
    error_message TEXT,
    FOREIGN KEY (competitor_id) REFERENCES competitors(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_scraped ON price_history(scraped_at);
CREATE INDEX IF NOT EXISTS idx_price_history_composite ON price_history(product_id, competitor_id, scraped_at);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_price_alerts_product ON price_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_created ON price_alerts(created_at);
"""


class DatabaseManager:
    """Manages database connections and schema for the price monitor."""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.SQLITE_DB_PATH
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema if tables don't exist."""
        with self.get_connection() as conn:
            conn.executescript(SQLITE_SCHEMA)
            logger.info("Database schema initialized at %s", self.db_path)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query, params=None):
        """Execute a single query and return results."""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.fetchall()

    def execute_many(self, query, params_list):
        """Execute a query with multiple parameter sets (batch insert)."""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            return conn.total_changes

    def get_or_create_competitor(self, name, base_url=None):
        """Get competitor ID or create if not exists. Returns ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM competitors WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return row["id"]
            cursor = conn.execute(
                "INSERT INTO competitors (name, base_url) VALUES (?, ?)",
                (name, base_url)
            )
            return cursor.lastrowid

    def get_or_create_category(self, name):
        """Get category ID or create if not exists. Returns ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM categories WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return row["id"]
            cursor = conn.execute(
                "INSERT INTO categories (name) VALUES (?)", (name,)
            )
            return cursor.lastrowid

    def upsert_product(self, sku, name, category_id, attributes_json,
                       source_competitor_id):
        """Insert or update a product. Returns product ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, attributes FROM products WHERE sku = ?", (sku,)
            ).fetchone()

            if row:
                # Merge JSON attributes
                existing_attrs = json.loads(row["attributes"] or "{}")
                new_attrs = json.loads(attributes_json or "{}")
                merged = {**existing_attrs, **new_attrs}
                conn.execute(
                    """UPDATE products
                       SET name = ?, category_id = ?, attributes = ?,
                           source_competitor_id = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (name, category_id, json.dumps(merged),
                     source_competitor_id, row["id"])
                )
                return row["id"]
            else:
                cursor = conn.execute(
                    """INSERT INTO products (sku, name, category_id, attributes,
                                            source_competitor_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sku, name, category_id, attributes_json,
                     source_competitor_id)
                )
                return cursor.lastrowid

    def insert_price(self, product_id, competitor_id, price, currency="USD",
                     in_stock=True):
        """Insert a new price history record."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO price_history
                   (product_id, competitor_id, price, currency, in_stock)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, competitor_id, price, currency, int(in_stock))
            )

    def get_last_price(self, product_id, competitor_id):
        """Get the most recent price for a product from a competitor."""
        with self.get_connection() as conn:
            row = conn.execute(
                """SELECT price, in_stock FROM price_history
                   WHERE product_id = ? AND competitor_id = ?
                   ORDER BY scraped_at DESC LIMIT 1""",
                (product_id, competitor_id)
            ).fetchone()
            if row:
                return {"price": row["price"], "in_stock": bool(row["in_stock"])}
            return None

    def insert_alert(self, product_id, alert_type, old_price, new_price,
                     pct_change):
        """Insert a price alert."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO price_alerts
                   (product_id, alert_type, old_price, new_price, pct_change)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, alert_type, old_price, new_price, pct_change)
            )

    def start_scrape_run(self, competitor_id):
        """Record the start of a scrape run. Returns run ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO scrape_runs
                   (competitor_id, started_at, status)
                   VALUES (?, CURRENT_TIMESTAMP, 'running')""",
                (competitor_id,)
            )
            return cursor.lastrowid

    def complete_scrape_run(self, run_id, products_scraped, status="completed",
                            error_message=None):
        """Mark a scrape run as completed or failed."""
        with self.get_connection() as conn:
            conn.execute(
                """UPDATE scrape_runs
                   SET completed_at = CURRENT_TIMESTAMP,
                       products_scraped = ?, status = ?, error_message = ?
                   WHERE id = ?""",
                (products_scraped, status, error_message, run_id)
            )
