"""
ETL Pipeline Orchestrator.
Ties together Extract → Transform → Load in sequence with logging and run tracking.
"""
import time
import json
import logging
from datetime import datetime
from pathlib import Path

from .database import DatabaseManager
from .scrapers.fakestore_scraper import FakeStoreScraper
from .scrapers.dummyjson_scraper import DummyJSONScraper
from .transform import transform_batch
from .load import DataLoader

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the full ETL pipeline for all competitor sources."""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self.loader = DataLoader(self.db)
        self.scrapers = {
            "FakeStore": FakeStoreScraper(),
            "DummyJSON": DummyJSONScraper(),
        }
        self.run_stats = {}

    def run(self, sources: list[str] = None) -> dict:
        """
        Execute the full ETL pipeline.

        Args:
            sources: List of competitor names to scrape.
                     Defaults to all configured sources.

        Returns:
            dict with overall stats and per-source breakdowns.
        """
        if sources is None:
            sources = list(self.scrapers.keys())

        logger.info("=" * 60)
        logger.info("Pipeline started at %s", datetime.now().isoformat())
        logger.info("Sources: %s", ", ".join(sources))
        logger.info("=" * 60)

        overall_start = time.time()
        total_stats = {
            "sources_processed": 0,
            "total_products": 0,
            "total_prices": 0,
            "total_alerts": 0,
            "total_errors": 0,
            "per_source": {},
        }

        for source_name in sources:
            if source_name not in self.scrapers:
                logger.warning("Unknown source: %s. Skipping.", source_name)
                continue

            source_stats = self._process_source(source_name)
            total_stats["per_source"][source_name] = source_stats
            total_stats["sources_processed"] += 1
            total_stats["total_products"] += source_stats.get("products_loaded", 0)
            total_stats["total_prices"] += source_stats.get("prices_recorded", 0)
            total_stats["total_alerts"] += source_stats.get("alerts_generated", 0)
            total_stats["total_errors"] += source_stats.get("errors", 0)

        elapsed = round(time.time() - overall_start, 2)
        total_stats["elapsed_seconds"] = elapsed

        logger.info("=" * 60)
        logger.info("Pipeline completed in %.2f seconds", elapsed)
        logger.info(
            "Total: %d products, %d prices, %d alerts, %d errors",
            total_stats["total_products"],
            total_stats["total_prices"],
            total_stats["total_alerts"],
            total_stats["total_errors"],
        )
        logger.info("=" * 60)

        self.run_stats = total_stats
        return total_stats

    def _process_source(self, source_name: str) -> dict:
        """Process a single competitor source through the E→T→L pipeline."""
        scraper = self.scrapers[source_name]
        source_config = config.COMPETITOR_SOURCES.get(source_name, {})
        base_url = source_config.get("base_url", "")

        # Start tracking this run
        competitor_id = self.db.get_or_create_competitor(source_name, base_url)
        run_id = self.db.start_scrape_run(competitor_id)

        try:
            # ── EXTRACT ──────────────────────────────────────────────
            logger.info("[%s] Phase 1: EXTRACT", source_name)
            raw_products = scraper.scrape()
            logger.info("[%s] Extracted %d products", source_name, len(raw_products))

            # ── TRANSFORM ────────────────────────────────────────────
            logger.info("[%s] Phase 2: TRANSFORM", source_name)
            transformed = transform_batch(raw_products, source_name)
            logger.info("[%s] Transformed %d products", source_name, len(transformed))

            # ── LOAD ─────────────────────────────────────────────────
            logger.info("[%s] Phase 3: LOAD", source_name)
            load_stats = self.loader.load_products(
                transformed, source_name, base_url
            )

            # Mark run as completed
            self.db.complete_scrape_run(
                run_id, load_stats["products_loaded"], "completed"
            )

            return load_stats

        except Exception as e:
            logger.error("[%s] Pipeline failed: %s", source_name, e)
            self.db.complete_scrape_run(run_id, 0, "failed", str(e))
            return {"products_loaded": 0, "prices_recorded": 0,
                    "alerts_generated": 0, "errors": 1, "error": str(e)}

    def run_seed(self) -> dict:
        """
        Load seed data from JSON file instead of scraping live APIs.
        Useful for demo/testing without network access.
        """
        seed_file = config.DATA_DIR / "seed_products.json"
        if not seed_file.exists():
            logger.error("Seed file not found: %s", seed_file)
            return {"error": "Seed file not found"}

        logger.info("Loading seed data from %s", seed_file)
        with open(seed_file, "r") as f:
            seed_data = json.load(f)

        total_stats = {
            "sources_processed": 0,
            "total_products": 0,
            "total_prices": 0,
            "total_alerts": 0,
            "total_errors": 0,
            "per_source": {},
            "mode": "seed",
        }

        for source_name, products in seed_data.items():
            from .scrapers.base_scraper import ProductData
            product_list = [
                ProductData(**p) for p in products
            ]
            transformed = transform_batch(product_list, source_name)

            source_config = config.COMPETITOR_SOURCES.get(source_name, {})
            load_stats = self.loader.load_products(
                transformed, source_name, source_config.get("base_url", "")
            )

            total_stats["per_source"][source_name] = load_stats
            total_stats["sources_processed"] += 1
            total_stats["total_products"] += load_stats["products_loaded"]
            total_stats["total_prices"] += load_stats["prices_recorded"]
            total_stats["total_alerts"] += load_stats["alerts_generated"]
            total_stats["total_errors"] += load_stats["errors"]

        return total_stats
