"""
Unit tests for the transform module.
Tests data normalization, SKU generation, JSON building, and price alerting.
"""
import json
import pytest

from src.transform import (
    normalize_name,
    generate_sku,
    clean_price,
    normalize_category,
    build_attributes_json,
    calculate_price_change,
    detect_stock_change,
    transform_product,
    transform_batch,
)
from src.scrapers.base_scraper import ProductData


class TestNormalizeName:
    def test_strips_whitespace(self):
        assert normalize_name("  Hello World  ") == "Hello World"

    def test_collapses_spaces(self):
        assert normalize_name("Too   Many    Spaces") == "Too Many Spaces"

    def test_empty_string(self):
        assert normalize_name("") == ""


class TestGenerateSku:
    def test_basic_sku(self):
        assert generate_sku("FakeStore", "42") == "FAK-42"

    def test_long_competitor(self):
        assert generate_sku("DummyJSON", "1") == "DUM-1"

    def test_short_competitor(self):
        assert generate_sku("AB", "99") == "AB-99"


class TestCleanPrice:
    def test_normal_price(self):
        assert clean_price(29.999) == 30.0

    def test_negative_price(self):
        assert clean_price(-5.0) == 0.0

    def test_none_price(self):
        assert clean_price(None) == 0.0

    def test_zero_price(self):
        assert clean_price(0) == 0.0


class TestNormalizeCategory:
    def test_basic(self):
        assert normalize_category("electronics") == "Electronics"

    def test_with_hyphens(self):
        assert normalize_category("men's-clothing") == "Men'S Clothing"

    def test_with_underscores(self):
        assert normalize_category("home_garden") == "Home Garden"

    def test_empty(self):
        assert normalize_category("") == "Uncategorized"

    def test_none(self):
        assert normalize_category(None) == "Uncategorized"


class TestBuildAttributesJson:
    def test_filters_empty_values(self):
        p = ProductData(
            source_id="1", name="Test", price=10.0,
            attributes={"brand": "Nike", "color": "", "tags": [], "size": None}
        )
        result = json.loads(build_attributes_json(p))
        assert "brand" in result
        assert "color" not in result
        assert "tags" not in result
        assert "size" not in result

    def test_preserves_nested_objects(self):
        p = ProductData(
            source_id="1", name="Test", price=10.0,
            description="Hello world",
            attributes={"dimensions": {"width": 10, "height": 20}}
        )
        result = json.loads(build_attributes_json(p))
        assert result["dimensions"]["width"] == 10
        assert result["description_length"] == 11


class TestCalculatePriceChange:
    def test_price_drop(self):
        result = calculate_price_change(100.0, 90.0)
        assert result["delta"] == -10.0
        assert result["pct_change"] == -10.0
        assert result["alert_type"] == "price_drop"

    def test_price_increase(self):
        result = calculate_price_change(100.0, 115.0)
        assert result["delta"] == 15.0
        assert result["pct_change"] == 15.0
        assert result["alert_type"] == "price_increase"

    def test_small_change_no_alert(self):
        result = calculate_price_change(100.0, 98.0)
        assert result["alert_type"] is None

    def test_no_change(self):
        result = calculate_price_change(50.0, 50.0)
        assert result["delta"] == 0
        assert result["alert_type"] is None

    def test_no_previous_price(self):
        result = calculate_price_change(None, 50.0)
        assert result["alert_type"] is None


class TestDetectStockChange:
    def test_went_out_of_stock(self):
        assert detect_stock_change(True, False) == "out_of_stock"

    def test_back_in_stock(self):
        assert detect_stock_change(False, True) == "back_in_stock"

    def test_no_change(self):
        assert detect_stock_change(True, True) is None

    def test_first_time(self):
        assert detect_stock_change(None, True) is None


class TestTransformBatch:
    def test_filters_invalid_records(self):
        products = [
            ProductData(source_id="1", name="Valid Product", price=10.0),
            ProductData(source_id="2", name="", price=20.0),  # empty name
            ProductData(source_id="3", name="Negative Price", price=-5.0),  # bad price
            ProductData(source_id="4", name="Another Valid", price=30.0),
        ]
        result = transform_batch(products, "TestSource")
        assert len(result) == 2
        assert result[0]["name"] == "Valid Product"
        assert result[1]["name"] == "Another Valid"

    def test_transform_output_structure(self):
        products = [
            ProductData(
                source_id="42", name="  Widget  ", price=19.999,
                category="gadgets", in_stock=True,
                attributes={"brand": "Acme"}
            )
        ]
        result = transform_batch(products, "FakeStore")
        assert len(result) == 1
        record = result[0]
        assert record["sku"] == "FAK-42"
        assert record["name"] == "Widget"
        assert record["price"] == 20.0
        assert record["category"] == "Gadgets"
        assert '"brand": "Acme"' in record["attributes_json"]
