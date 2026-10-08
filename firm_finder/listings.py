"""Pulls active California land listings from Realtor.com, county by county,
using the HomeHarvest library. Each listing carries the listing agent, office
and broker, which is how we find the firms that do land deals."""

import random
import time

import pandas as pd

import config
from common import setup_logger

logger = setup_logger("listings")


def _scrape_county(county: str) -> pd.DataFrame:
    from homeharvest import scrape_property  # imported here so tests don't need it

    location = f"{county} County, {config.STATE}"
    last_error = None
    for attempt in range(1, config.LISTING_RETRIES + 1):
        try:
            df = scrape_property(
                location=location,
                listing_type="for_sale",
                property_type=config.LISTING_PROPERTY_TYPES,
                proxy=config.PROXY,
                extra_property_data=False,
            )
            df = df if df is not None else pd.DataFrame()
            df["search_county"] = county
            return df
        except Exception as e:  # noqa: BLE001 - one county must not kill the run
            last_error = e
            wait = 20 * attempt + random.uniform(0, 10)
            logger.warning("%s: attempt %d/%d failed (%s). Waiting %.0fs.",
                           location, attempt, config.LISTING_RETRIES, e, wait)
            time.sleep(wait)
    logger.error("%s: giving up after %d attempts: %s", location, config.LISTING_RETRIES, last_error)
    return pd.DataFrame()


def pull_land_listings(counties: list[str]) -> pd.DataFrame:
    frames = []
    for i, county in enumerate(counties, 1):
        df = _scrape_county(county)
        logger.info("[%d/%d] %s County: %d land listings", i, len(counties), county, len(df))
        if not df.empty:
            frames.append(df)
        if i < len(counties):
            time.sleep(random.uniform(*config.DELAY_BETWEEN_COUNTIES))

    if not frames:
        return pd.DataFrame()
    listings = pd.concat(frames, ignore_index=True)
    if "property_id" in listings.columns:
        listings = listings.drop_duplicates(subset="property_id")
    return listings
