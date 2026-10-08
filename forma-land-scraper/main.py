"""Entry point: scrape configured sources, filter, dedupe, export CSVs.

Usage:
    python main.py                       # run all sources with SEARCH_URLS configured
    python main.py --source landwatch    # run just one source
    python main.py --min-acres 5 --max-acres 40
"""

import argparse

import config
from browser import new_page
from dedup import dedupe_by_agent
from export_csv import write_instantly_csv, write_raw_listings_csv
from models import Listing
from scrapers import landwatch
from utils import setup_logger

logger = setup_logger("main")

SCRAPERS = {
    "landwatch": landwatch,
    # "zillow": zillow,     # add once landwatch is confirmed working end-to-end
    # "loopnet": loopnet,
}


def run(sources: list[str], min_acres: float, max_acres: float) -> None:
    all_listings: list[Listing] = []

    for source in sources:
        search_urls = config.SEARCH_URLS.get(source, [])
        if not search_urls:
            logger.warning("No SEARCH_URLS configured for '%s' in config.py — skipping.", source)
            continue

        scraper = SCRAPERS.get(source)
        if not scraper:
            logger.warning("No scraper implemented yet for '%s' — skipping.", source)
            continue

        logger.info("=== Starting source: %s ===", source)
        with new_page() as page:
            try:
                results = scraper.scrape(page, search_urls)
            except Exception as e:
                logger.error("Source '%s' failed entirely: %s", source, e)
                continue

        logger.info("Source '%s' returned %d raw listings.", source, len(results))
        all_listings.extend(results)

    if not all_listings:
        logger.warning("No listings scraped this run. Check SEARCH_URLS in config.py "
                        "and confirm selectors against live HTML (see landwatch.py header).")
        return

    filtered = [l for l in all_listings if l.passes_acreage_filter(min_acres, max_acres)]
    logger.info("%d/%d listings passed acreage filter (%.1f-%.1f acres).",
                len(filtered), len(all_listings), min_acres, max_acres)

    agent_records = dedupe_by_agent(filtered)
    logger.info("Deduped to %d unique agents.", len(agent_records))

    raw_path = write_raw_listings_csv(filtered, config.OUTPUT_DIR)
    instantly_path = write_instantly_csv(agent_records, config.OUTPUT_DIR)

    print(f"\nDone.\n  Raw listings CSV:     {raw_path}\n  Instantly import CSV: {instantly_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forma Designs land-listing scraper")
    parser.add_argument("--source", action="append", dest="sources",
                         help="Source to scrape (landwatch, zillow, loopnet). Repeatable. Default: all configured.")
    parser.add_argument("--min-acres", type=float, default=config.MIN_ACRES)
    parser.add_argument("--max-acres", type=float, default=config.MAX_ACRES)
    args = parser.parse_args()

    sources = args.sources or list(SCRAPERS.keys())
    run(sources, args.min_acres, args.max_acres)
