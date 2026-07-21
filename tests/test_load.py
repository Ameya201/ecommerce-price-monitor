"""
Integration tests for the data loading module.
Tests upsert logic, price tracking, and alert generation.
"""
import json
import pytest
import tempfile
from pathlib import Path

from src.database import DatabaseManager
from src.load import DataLoader
from src.transform import transform_batch
from src.scrapers.base_scraper import ProductData


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return DatabaseManager(db_path=db_path)


@pytest.fixture
def loader(db):
    """Create a DataLoader with the test database."""
    return DataLoader(db)


@pytest.fixture
def sample_products():
    """Create sample transformed product records."""
    products = [
        ProductData(
            source_id="1", name="Test Widget", price=29.99,
            category="electronics", in_stock=True,
            attributes={"brand": "Acme", "weight_g": 100}
        ),
        ProductData(
            source_id="2", name="Test Gadget", price=49.99,
            category="electronics", in_stock=True,
            attributes={"brand": "BetaCorp", "color": "blue"}
        ),
    ]
    return transform_batch(products, "TestStore")


class TestDatabaseManager:
    def test_create_competitor(self, db):
        cid = db.get_or_create_competitor("TestStore", "https://test.com")
        assert cid > 0
        # Getting same name returns same ID
        cid2 = db.get_or_create_competitor("TestStore")
        assert cid2 == cid

    def test_create_category(self, db):
        cat_id = db.get_or_create_category("Electronics")
        assert cat_id > 0
        cat_id2 = db.get_or_create_category("Electronics")
        assert cat_id2 == cat_id

    def test_upsert_product_insert(self, db):
        db.get_or_create_competitor("TestStore")
        db.get_or_create_category("Electronics")
        pid = db.upsert_product(
            sku="TST-1", name="Widget", category_id=1,
            attributes_json='{"brand": "Acme"}',
            source_competitor_id=1
        )
        assert pid > 0

    def test_upsert_product_update_merges_json(self, db):
        db.get_or_create_competitor("TestStore")
        db.get_or_create_category("Electronics")
        pid1 = db.upsert_product(
            sku="TST-1", name="Widget", category_id=1,
            attributes_json='{"brand": "Acme"}',
            source_competitor_id=1
        )
        pid2 = db.upsert_product(
            sku="TST-1", name="Widget V2", category_id=1,
            attributes_json='{"color": "red"}',
            source_competitor_id=1
        )
        assert pid2 == pid1  # Same product, updated

        # Verify JSON was merged
        rows = db.execute("SELECT attributes FROM products WHERE id = ?", (pid1,))
        attrs = json.loads(rows[0]["attributes"])
        assert attrs["brand"] == "Acme"
        assert attrs["color"] == "red"

    def test_price_history(self, db):
        cid = db.get_or_create_competitor("TestStore")
        cat_id = db.get_or_create_category("Electronics")
        pid = db.upsert_product("TST-1", "Widget", cat_id, '{}', cid)

        db.insert_price(pid, cid, 29.99)
        last = db.get_last_price(pid, cid)
        assert last["price"] == 29.99
        assert last["in_stock"] is True


class TestDataLoader:
    def test_load_products(self, loader, sample_products):
        stats = loader.load_products(sample_products, "TestStore", "https://test.com")
        assert stats["products_loaded"] == 2
        assert stats["prices_recorded"] == 2
        assert stats["errors"] == 0

    def test_reload_same_products_no_alerts(self, loader, sample_products):
        """Loading same products twice should not generate alerts (same price)."""
        loader.load_products(sample_products, "TestStore")
        # Reset stats
        stats = loader.load_products(sample_products, "TestStore")
        assert stats["alerts_generated"] == 0

    def test_price_drop_generates_alert(self, loader, db):
        """A significant price drop should generate an alert."""
        products_v1 = transform_batch([
            ProductData(source_id="1", name="Widget", price=100.0,
                        category="test", in_stock=True, attributes={})
        ], "TestStore")
        loader.load_products(products_v1, "TestStore")

        # Now load with a 20% price drop
        products_v2 = transform_batch([
            ProductData(source_id="1", name="Widget", price=80.0,
                        category="test", in_stock=True, attributes={})
        ], "TestStore")
        stats = loader.load_products(products_v2, "TestStore")
        assert stats["alerts_generated"] >= 1

        # Verify the alert exists in the database
        alerts = db.execute("SELECT * FROM price_alerts WHERE alert_type = 'price_drop'")
        assert len(alerts) >= 1

    def test_stock_change_generates_alert(self, loader, db):
        """Going out of stock should generate an alert."""
        products_v1 = transform_batch([
            ProductData(source_id="1", name="Widget", price=50.0,
                        category="test", in_stock=True, attributes={})
        ], "TestStore")
        loader.load_products(products_v1, "TestStore")

        products_v2 = transform_batch([
            ProductData(source_id="1", name="Widget", price=50.0,
                        category="test", in_stock=False, attributes={})
        ], "TestStore")
        stats = loader.load_products(products_v2, "TestStore")
        assert stats["alerts_generated"] >= 1

        alerts = db.execute("SELECT * FROM price_alerts WHERE alert_type = 'out_of_stock'")
        assert len(alerts) >= 1
