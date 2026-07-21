"""
Scraper for DummyJSON (https://dummyjson.com)
Free, no-auth REST API with rich product attributes — ideal for JSON column demo.
"""
import logging

from .base_scraper import BaseScraper, ProductData

logger = logging.getLogger(__name__)


class DummyJSONScraper(BaseScraper):
    """Scrapes product data from DummyJSON API."""

    def __init__(self):
        super().__init__(
            competitor_name="DummyJSON",
            base_url="https://dummyjson.com"
        )

    def scrape(self) -> list[ProductData]:
        """Fetch all products from DummyJSON and return standardized data."""
        logger.info("[DummyJSON] Starting product scrape...")

        data = self._make_request("/products", params={"limit": 100})
        raw_products = data.get("products", [])

        products = []
        for item in raw_products:
            try:
                product = self._parse_product(item)
                products.append(product)
            except (KeyError, ValueError) as e:
                logger.warning(
                    "[DummyJSON] Skipping product %s: %s",
                    item.get("id", "unknown"), e
                )

        logger.info("[DummyJSON] Scraped %d products", len(products))
        return products

    def _parse_product(self, item: dict) -> ProductData:
        """Parse a single DummyJSON item into ProductData."""
        # DummyJSON provides much richer attributes — great for JSON column
        dimensions = item.get("dimensions", {})
        meta = item.get("meta", {})
        reviews = item.get("reviews", [])

        attributes = {
            "brand": item.get("brand", ""),
            "sku_original": item.get("sku", ""),
            "weight_g": item.get("weight", 0),
            "dimensions": {
                "width": dimensions.get("width", 0),
                "height": dimensions.get("height", 0),
                "depth": dimensions.get("depth", 0),
            },
            "warranty_info": item.get("warrantyInformation", ""),
            "shipping_info": item.get("shippingInformation", ""),
            "availability_status": item.get("availabilityStatus", ""),
            "return_policy": item.get("returnPolicy", ""),
            "minimum_order_qty": item.get("minimumOrderQuantity", 1),
            "tags": item.get("tags", []),
            "rating_score": item.get("rating", 0),
            "review_count": len(reviews),
            "discount_pct": item.get("discountPercentage", 0),
            "thumbnail": item.get("thumbnail", ""),
            "images": item.get("images", []),
            "barcode": meta.get("barcode", ""),
            "qr_code": meta.get("qrCode", ""),
            "source_api": "dummyjson.com",
        }

        # Determine stock status
        avail = item.get("availabilityStatus", "In Stock")
        in_stock = avail.lower() in ("in stock", "low stock")

        return ProductData(
            source_id=str(item["id"]),
            name=item["title"],
            price=float(item["price"]),
            currency="USD",
            category=item.get("category", "uncategorized"),
            in_stock=in_stock,
            description=item.get("description", ""),
            image_url=item.get("thumbnail", ""),
            attributes=attributes,
        )
