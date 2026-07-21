"""
E-Commerce Competitor Price Monitor — Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SQLITE_DB_PATH = DATA_DIR / "price_monitor.db"

# ── Database ──────────────────────────────────────────────────────────────
DB_MODE = os.getenv("DB_MODE", "sqlite")  # 'sqlite' or 'mysql'

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "price_monitor"),
}

# ── API Endpoints (Competitor Sources) ────────────────────────────────────
COMPETITOR_SOURCES = {
    "FakeStore": {
        "base_url": "https://fakestoreapi.com",
        "products_endpoint": "/products",
    },
    "DummyJSON": {
        "base_url": "https://dummyjson.com",
        "products_endpoint": "/products?limit=100",
    },
}

# ── Scraper Settings ─────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30          # seconds
REQUEST_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
RATE_LIMIT_DELAY = 1.0        # seconds between requests

# ── Alert Thresholds ─────────────────────────────────────────────────────
PRICE_DROP_THRESHOLD_PCT = 5.0     # alert if price drops > 5%
PRICE_INCREASE_THRESHOLD_PCT = 10.0  # alert if price increases > 10%

# ── Dashboard ────────────────────────────────────────────────────────────
DASHBOARD_THEME = "dark"
DASHBOARD_TITLE = "🛍️ E-Commerce Price Monitor"
