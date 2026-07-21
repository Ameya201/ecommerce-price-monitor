"""
Data transformation module.
Normalizes scraped product data, builds JSON attribute objects,
generates deterministic SKUs, and detects price changes for alerting.
"""
import re
import json
import hashlib
import logging
from typing import Optional

from .scrapers.base_scraper import ProductData

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize product name:
    - Strip leading/trailing whitespace
    - Collapse multiple spaces
    - Title case
    """
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    return name


def generate_sku(competitor_name: str, source_id: str) -> str:
    """
    Generate a deterministic SKU from competitor + source ID.
    Format: PREFIX-SOURCEID (e.g., FAK-1, DUM-42)
    """
    prefix = competitor_name.upper()[:3]
    return f"{prefix}-{source_id}"


def clean_price(price: float) -> float:
    """Ensure price is a valid positive number, rounded to 2 decimals."""
    if price is None or price < 0:
        return 0.0
    return round(float(price), 2)


def normalize_category(category: str) -> str:
    """Normalize category name to title case, stripped."""
    if not category:
        return "Uncategorized"
    return category.strip().replace("-", " ").replace("_", " ").title()


def build_attributes_json(product: ProductData) -> str:
    """
    Build a clean JSON string from product attributes.
    Filters out empty/null values to keep the JSON lean.
    """
    attrs = {}
    for key, value in product.attributes.items():
        # Skip empty strings, None, empty lists, and zero values
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        attrs[key] = value

    # Add computed fields
    if product.description:
        attrs["description_length"] = len(product.description)

    return json.dumps(attrs, ensure_ascii=False)


def calculate_price_change(old_price: float, new_price: float) -> dict:
    """
    Calculate price change metrics.
    Returns dict with delta, pct_change, and alert_type.
    """
    if old_price is None or old_price == 0:
        return {"delta": 0, "pct_change": 0, "alert_type": None}

    delta = new_price - old_price
    pct_change = round((delta / old_price) * 100, 2)

    alert_type = None
    if pct_change < 0 and abs(pct_change) >= 5.0:
        alert_type = "price_drop"
    elif pct_change > 0 and pct_change >= 10.0:
        alert_type = "price_increase"

    return {
        "delta": round(delta, 2),
        "pct_change": pct_change,
        "alert_type": alert_type,
    }


def detect_stock_change(was_in_stock: Optional[bool],
                        is_in_stock: bool) -> Optional[str]:
    """Detect stock status changes."""
    if was_in_stock is None:
        return None
    if was_in_stock and not is_in_stock:
        return "out_of_stock"
    if not was_in_stock and is_in_stock:
        return "back_in_stock"
    return None


def transform_product(product: ProductData,
                      competitor_name: str) -> dict:
    """
    Apply all transformations to a single ProductData instance.
    Returns a dict ready for database loading.
    """
    return {
        "sku": generate_sku(competitor_name, product.source_id),
        "name": normalize_name(product.name),
        "price": clean_price(product.price),
        "currency": product.currency or "USD",
        "category": normalize_category(product.category),
        "in_stock": product.in_stock,
        "attributes_json": build_attributes_json(product),
    }


def transform_batch(products: list[ProductData],
                     competitor_name: str) -> list[dict]:
    """
    Transform a batch of products.
    Filters out invalid records and logs statistics.
    """
    transformed = []
    skipped = 0

    for product in products:
        # Validate required fields
        if not product.name or not product.name.strip():
            logger.warning("Skipping product with empty name: %s", product.source_id)
            skipped += 1
            continue

        if product.price is None or product.price < 0:
            logger.warning("Skipping product with invalid price: %s", product.name)
            skipped += 1
            continue

        record = transform_product(product, competitor_name)
        transformed.append(record)

    logger.info(
        "Transformed %d products (%d skipped) from %s",
        len(transformed), skipped, competitor_name
    )
    return transformed
