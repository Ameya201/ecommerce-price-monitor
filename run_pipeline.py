#!/usr/bin/env python3
"""
E-Commerce Competitor Price Monitor — CLI Entry Point

Usage:
    python run_pipeline.py              # Run full pipeline (scrape live APIs)
    python run_pipeline.py --seed       # Load seed data (no network needed)
    python run_pipeline.py --source FakeStore  # Scrape only FakeStore
"""
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import Pipeline


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
        datefmt="%H:%M:%S",
    )


def print_report(stats: dict):
    """Print a formatted summary report."""
    print("\n" + "═" * 60)
    print("  🛍️  E-COMMERCE PRICE MONITOR — PIPELINE REPORT")
    print("═" * 60)

    mode = stats.get("mode", "live")
    print(f"  Mode:              {'Seed Data' if mode == 'seed' else 'Live API'}")
    print(f"  Sources Processed: {stats.get('sources_processed', 0)}")
    print(f"  Total Products:    {stats.get('total_products', 0)}")
    print(f"  Prices Recorded:   {stats.get('total_prices', 0)}")
    print(f"  Alerts Generated:  {stats.get('total_alerts', 0)}")
    print(f"  Errors:            {stats.get('total_errors', 0)}")

    if "elapsed_seconds" in stats:
        print(f"  Duration:          {stats['elapsed_seconds']:.2f}s")

    # Per-source breakdown
    per_source = stats.get("per_source", {})
    if per_source:
        print("\n  ── Per Source ──")
        for source, ss in per_source.items():
            status = "✅" if ss.get("errors", 0) == 0 else "⚠️"
            print(
                f"  {status} {source:12s} │ "
                f"{ss.get('products_loaded', 0):3d} products │ "
                f"{ss.get('prices_recorded', 0):3d} prices │ "
                f"{ss.get('alerts_generated', 0):2d} alerts"
            )

    print("═" * 60)

    if stats.get("total_errors", 0) == 0:
        print("  ✅ Pipeline completed successfully!")
    else:
        print(f"  ⚠️  Pipeline completed with {stats['total_errors']} error(s)")

    print(f"\n  Dashboard: streamlit run dashboard/app.py")
    print("═" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="E-Commerce Competitor Price Monitor ETL Pipeline"
    )
    parser.add_argument(
        "--seed", action="store_true",
        help="Load seed data instead of scraping live APIs"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Scrape only a specific source (e.g., FakeStore, DummyJSON)"
    )
    args = parser.parse_args()

    setup_logging()

    pipeline = Pipeline()

    if args.seed:
        stats = pipeline.run_seed()
    elif args.source:
        stats = pipeline.run(sources=[args.source])
    else:
        stats = pipeline.run()

    print_report(stats)

    # Exit with error code if there were errors
    sys.exit(1 if stats.get("total_errors", 0) > 0 else 0)


if __name__ == "__main__":
    main()
