"""
Abstract base class for all scrapers.
Each scraper must implement the `scrape()` method returning standardized ProductData.
"""
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config

logger = logging.getLogger(__name__)


@dataclass
class ProductData:
    """Standardized product data returned by all scrapers."""
    source_id: str            # Original ID from the source API
    name: str
    price: float
    currency: str = "USD"
    category: str = ""
    in_stock: bool = True
    description: str = ""
    image_url: str = ""
    attributes: dict = field(default_factory=dict)
    # attributes can include: brand, color, size, weight, dimensions,
    #                         rating, review_count, tags, specs, etc.


class BaseScraper(ABC):
    """Base class for all competitor scrapers."""

    def __init__(self, competitor_name: str, base_url: str):
        self.competitor_name = competitor_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PriceMonitor/1.0 (Educational Project)",
            "Accept": "application/json",
        })

    @abstractmethod
    def scrape(self) -> list[ProductData]:
        """
        Fetch and return all products from this competitor.
        Must be implemented by each scraper subclass.
        """
        pass

    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """
        Make an HTTP GET request with retry logic and rate limiting.
        Returns parsed JSON response.
        """
        url = f"{self.base_url}{endpoint}"
        last_error = None

        for attempt in range(1, config.REQUEST_RETRIES + 1):
            try:
                logger.info(
                    "[%s] Request attempt %d/%d: %s",
                    self.competitor_name, attempt, config.REQUEST_RETRIES, url
                )
                response = self.session.get(
                    url, params=params, timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()

                # Rate limiting
                time.sleep(config.RATE_LIMIT_DELAY)

                return response.json()

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(
                    "[%s] Request failed (attempt %d/%d): %s",
                    self.competitor_name, attempt, config.REQUEST_RETRIES, e
                )
                if attempt < config.REQUEST_RETRIES:
                    backoff = config.RETRY_BACKOFF_FACTOR * attempt
                    logger.info("Retrying in %.1f seconds...", backoff)
                    time.sleep(backoff)

        raise ConnectionError(
            f"[{self.competitor_name}] Failed after {config.REQUEST_RETRIES} "
            f"attempts: {last_error}"
        )

    def _generate_sku(self, source_id: str) -> str:
        """Generate a deterministic SKU from competitor name + source ID."""
        prefix = self.competitor_name.upper()[:3]
        return f"{prefix}-{source_id}"
