"""
Data loading module.
Handles upserting transformed product data into the database,
inserting price history, and generating alerts.
"""
import json
import logging

from .database import DatabaseManager
from .transform import calculate_price_change, detect_stock_change

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads transformed product data into the database."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.stats = {
            "products_loaded": 0,
            "prices_recorded": 0,
            "alerts_generated": 0,
            "errors": 0,
        }

    def load_products(self, transformed_records: list[dict],
                      competitor_name: str, base_url: str = None) -> dict:
        """
        Load a batch of transformed product records into the database.

        For each product:
        1. Ensure competitor and category exist
        2. Upsert the product (with JSON attribute merge)
        3. Insert price history record
        4. Check for price changes and generate alerts

        Returns stats dict.
        """
        self.stats = {
            "products_loaded": 0,
            "prices_recorded": 0,
            "alerts_generated": 0,
            "errors": 0,
        }

        # Get or create competitor
        competitor_id = self.db.get_or_create_competitor(
            competitor_name, base_url
        )

        for record in transformed_records:
            try:
                self._load_single_product(record, competitor_id)
            except Exception as e:
                logger.error(
                    "Error loading product %s: %s",
                    record.get("sku", "unknown"), e
                )
                self.stats["errors"] += 1

        logger.info(
            "Load complete for %s: %d products, %d prices, %d alerts, %d errors",
            competitor_name,
            self.stats["products_loaded"],
            self.stats["prices_recorded"],
            self.stats["alerts_generated"],
            self.stats["errors"],
        )

        return self.stats.copy()

    def _load_single_product(self, record: dict, competitor_id: int):
        """Load a single product record into the database."""
        # 1. Get or create category
        category_id = self.db.get_or_create_category(record["category"])

        # 2. Upsert product
        product_id = self.db.upsert_product(
            sku=record["sku"],
            name=record["name"],
            category_id=category_id,
            attributes_json=record["attributes_json"],
            source_competitor_id=competitor_id,
        )
        self.stats["products_loaded"] += 1

        # 3. Check previous price for alerting
        last_price_data = self.db.get_last_price(product_id, competitor_id)

        # 4. Insert new price record
        self.db.insert_price(
            product_id=product_id,
            competitor_id=competitor_id,
            price=record["price"],
            currency=record["currency"],
            in_stock=record["in_stock"],
        )
        self.stats["prices_recorded"] += 1

        # 5. Generate alerts if price changed
        if last_price_data:
            self._check_and_alert(
                product_id=product_id,
                old_price=last_price_data["price"],
                new_price=record["price"],
                was_in_stock=last_price_data["in_stock"],
                is_in_stock=record["in_stock"],
            )

    def _check_and_alert(self, product_id: int, old_price: float,
                         new_price: float, was_in_stock: bool,
                         is_in_stock: bool):
        """Check for significant price or stock changes and generate alerts."""
        # Price change alert
        change = calculate_price_change(old_price, new_price)
        if change["alert_type"]:
            self.db.insert_alert(
                product_id=product_id,
                alert_type=change["alert_type"],
                old_price=old_price,
                new_price=new_price,
                pct_change=change["pct_change"],
            )
            self.stats["alerts_generated"] += 1
            logger.info(
                "Alert: %s for product %d (%.2f → %.2f, %.1f%%)",
                change["alert_type"], product_id,
                old_price, new_price, change["pct_change"]
            )

        # Stock change alert
        stock_alert = detect_stock_change(was_in_stock, is_in_stock)
        if stock_alert:
            self.db.insert_alert(
                product_id=product_id,
                alert_type=stock_alert,
                old_price=old_price,
                new_price=new_price,
                pct_change=0,
            )
            self.stats["alerts_generated"] += 1
            logger.info(
                "Alert: %s for product %d", stock_alert, product_id
            )
