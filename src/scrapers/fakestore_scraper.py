"""
Scraper for FakeStoreAPI (https://fakestoreapi.com)
Free, no-auth REST API providing product data for development.
"""
import logging

from .base_scraper import BaseScraper, ProductData

logger = logging.getLogger(__name__)


class FakeStoreScraper(BaseScraper):
    """Scrapes product data from FakeStoreAPI."""

    def __init__(self):
        super().__init__(
            competitor_name="FakeStore",
            base_url="https://fakestoreapi.com"
        )

    def scrape(self) -> list[ProductData]:
        """Fetch all products from FakeStoreAPI and return standardized data."""
        logger.info("[FakeStore] Starting product scrape...")

        raw_products = self._make_request("/products")

        products = []
        for item in raw_products:
            try:
                product = self._parse_product(item)
                products.append(product)
            except (KeyError, ValueError) as e:
                logger.warning(
                    "[FakeStore] Skipping product %s: %s",
                    item.get("id", "unknown"), e
                )

        logger.info("[FakeStore] Scraped %d products", len(products))
        return products

    def _parse_product(self, item: dict) -> ProductData:
        """Parse a single FakeStore API item into ProductData."""
        rating = item.get("rating", {})

        attributes = {
            "description": item.get("description", ""),
            "image_url": item.get("image", ""),
            "rating_score": rating.get("rate", 0),
            "rating_count": rating.get("count", 0),
            "source_api": "fakestoreapi.com",
        }

        return ProductData(
            source_id=str(item["id"]),
            name=item["title"],
            price=float(item["price"]),
            currency="USD",
            category=item.get("category", "uncategorized"),
            in_stock=True,  # FakeStore doesn't provide stock info
            description=item.get("description", ""),
            image_url=item.get("image", ""),
            attributes=attributes,
        )
