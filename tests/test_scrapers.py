"""
Unit tests for the scraper modules.
Tests output format, data parsing, and error handling.
"""
import pytest
from src.scrapers.base_scraper import ProductData
from src.scrapers.fakestore_scraper import FakeStoreScraper
from src.scrapers.dummyjson_scraper import DummyJSONScraper


class TestProductData:
    """Test the ProductData dataclass."""

    def test_default_values(self):
        p = ProductData(source_id="1", name="Test Product", price=9.99)
        assert p.currency == "USD"
        assert p.category == ""
        assert p.in_stock is True
        assert p.attributes == {}

    def test_full_product(self):
        p = ProductData(
            source_id="42",
            name="Test Widget",
            price=29.99,
            currency="EUR",
            category="electronics",
            in_stock=False,
            description="A test widget",
            image_url="https://example.com/img.jpg",
            attributes={"brand": "TestBrand", "weight_g": 100},
        )
        assert p.source_id == "42"
        assert p.price == 29.99
        assert p.attributes["brand"] == "TestBrand"


class TestFakeStoreScraper:
    """Test FakeStore scraper parsing logic."""

    def test_parse_product(self):
        scraper = FakeStoreScraper()
        raw = {
            "id": 1,
            "title": "Test Backpack",
            "price": 109.95,
            "description": "A sturdy backpack",
            "category": "men's clothing",
            "image": "https://example.com/img.jpg",
            "rating": {"rate": 3.9, "count": 120},
        }
        product = scraper._parse_product(raw)
        assert isinstance(product, ProductData)
        assert product.source_id == "1"
        assert product.name == "Test Backpack"
        assert product.price == 109.95
        assert product.category == "men's clothing"
        assert product.attributes["rating_score"] == 3.9
        assert product.attributes["rating_count"] == 120

    def test_parse_product_missing_rating(self):
        scraper = FakeStoreScraper()
        raw = {
            "id": 2,
            "title": "Simple Item",
            "price": 10.00,
            "description": "",
            "category": "other",
            "image": "",
            "rating": {},
        }
        product = scraper._parse_product(raw)
        assert product.attributes["rating_score"] == 0
        assert product.attributes["rating_count"] == 0


class TestDummyJSONScraper:
    """Test DummyJSON scraper parsing logic."""

    def test_parse_product(self):
        scraper = DummyJSONScraper()
        raw = {
            "id": 1,
            "title": "Essence Mascara",
            "price": 9.99,
            "description": "Popular mascara",
            "category": "beauty",
            "thumbnail": "https://example.com/thumb.jpg",
            "brand": "Essence",
            "weight": 50,
            "dimensions": {"width": 3, "height": 15, "depth": 3},
            "warrantyInformation": "1 year",
            "shippingInformation": "Ships in 1-2 weeks",
            "availabilityStatus": "In Stock",
            "returnPolicy": "30 days",
            "minimumOrderQuantity": 1,
            "tags": ["beauty", "mascara"],
            "rating": 4.94,
            "reviews": [{"body": "Great!"}],
            "discountPercentage": 7.17,
            "images": ["img1.jpg", "img2.jpg"],
            "meta": {"barcode": "1234567890", "qrCode": "https://qr.example.com"},
            "sku": "ORIG-SKU-1",
        }
        product = scraper._parse_product(raw)
        assert isinstance(product, ProductData)
        assert product.name == "Essence Mascara"
        assert product.price == 9.99
        assert product.in_stock is True
        assert product.attributes["brand"] == "Essence"
        assert product.attributes["weight_g"] == 50
        assert product.attributes["dimensions"]["width"] == 3
        assert product.attributes["tags"] == ["beauty", "mascara"]
        assert product.attributes["review_count"] == 1

    def test_out_of_stock(self):
        scraper = DummyJSONScraper()
        raw = {
            "id": 99,
            "title": "Out of Stock Item",
            "price": 5.00,
            "description": "",
            "category": "misc",
            "thumbnail": "",
            "availabilityStatus": "Out of Stock",
            "dimensions": {},
            "meta": {},
            "reviews": [],
        }
        product = scraper._parse_product(raw)
        assert product.in_stock is False
