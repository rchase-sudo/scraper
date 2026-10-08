"""LandWatch scraper.

VERIFY BEFORE TRUSTING OUTPUT: built without live access to landwatch.com
(the harness blocked the test fetch), so the CSS-selector fallbacks below are
best-guess based on common real-estate-listing markup patterns, not confirmed
against current live HTML. Run with config.HEADLESS = False and a low limit
first, watch it in the browser window, and use devtools "Inspect Element" on
a real search-results page + listing page to fix any selector marked VERIFY
if it isn't finding data.
"""

from urllib.parse import urljoin

import config
from models import Listing
from scrapers.common import (
    extract_json_ld,
    extract_mailto_email,
    extract_tel_phone,
    find_first_email_in_text,
)
from utils import parse_acreage, parse_price, polite_delay, retry_with_backoff, setup_logger

logger = setup_logger("landwatch")

SOURCE = "landwatch"


@retry_with_backoff()
def _goto(page, url: str):
    resp = page.goto(url, timeout=30000, wait_until="domcontentloaded")
    if resp and resp.status in (403, 429, 503):
        raise RuntimeError(f"Blocked/rate-limited: HTTP {resp.status} on {url}")
    page.wait_for_timeout(2500)  # let client-side rendering settle
    return resp


def get_listing_urls_from_search(page, search_url: str, max_pages: int) -> list[str]:
    """Collects listing detail-page URLs from a paginated search results page."""
    urls: list[str] = []
    current_url = search_url

    for page_num in range(1, max_pages + 1):
        logger.info("Fetching search results page %d: %s", page_num, current_url)
        try:
            _goto(page, current_url)
        except Exception as e:
            logger.error("Failed to load search page %s after retries: %s", current_url, e)
            break

        # VERIFY: listing card links. LandWatch listing detail URLs typically
        # contain "/pid/" or a numeric listing id — adjust this selector/filter
        # once you've inspected a real search-results page.
        anchors = page.query_selector_all('a[href*="/pid/"], a[href*="/property/"]')
        found_this_page = 0
        for a in anchors:
            href = a.get_attribute("href")
            if not href:
                continue
            full_url = urljoin(current_url, href)
            if full_url not in urls:
                urls.append(full_url)
                found_this_page += 1

        logger.info("Found %d new listing URLs on page %d (total so far: %d)",
                    found_this_page, page_num, len(urls))

        if found_this_page == 0:
            logger.info("No new listings found; assuming end of results.")
            break

        # VERIFY: "next page" link. Common patterns: rel="next", aria-label
        # "Next", or a page-number query param you can increment yourself.
        next_link = page.query_selector('a[rel="next"], a[aria-label="Next"]')
        if not next_link:
            logger.info("No next-page link found; stopping pagination.")
            break
        next_href = next_link.get_attribute("href")
        if not next_href:
            break
        current_url = urljoin(current_url, next_href)
        polite_delay()

    return urls


@retry_with_backoff()
def scrape_listing_detail(page, url: str) -> Listing | None:
    _goto(page, url)

    listing = Listing(source=SOURCE, listing_url=url)

    # --- Try structured data first (most robust) ---
    ld_blocks = extract_json_ld(page)
    for block in ld_blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("@type", "")
        if "RealEstate" in str(block_type) or "Product" in str(block_type) or "Offer" in str(block_type):
            offers = block.get("offers", {})
            if isinstance(offers, dict) and "price" in offers:
                listing.price = parse_price(str(offers["price"]))
            addr = block.get("address")
            if isinstance(addr, dict):
                listing.address = addr.get("streetAddress", "") or block.get("name", "")
                listing.city = addr.get("addressLocality", "")
                listing.state = addr.get("addressRegion", "")
            elif isinstance(addr, str):
                listing.address = addr

    # --- Fallback: page title / headline usually contains address ---
    if not listing.address:
        # VERIFY: adjust selector to whatever element holds the listing headline.
        headline = page.query_selector("h1")
        if headline:
            listing.address = headline.inner_text().strip()

    # --- Price ---
    if listing.price is None:
        # VERIFY: price is often in an element with "price" in its class name.
        price_el = page.query_selector('[class*="price" i]')
        if price_el:
            listing.price = parse_price(price_el.inner_text())

    # --- Acreage ---
    # VERIFY: acreage is often near "Lot Size" / "Acres" label text.
    acreage_el = page.query_selector('[class*="acre" i], [class*="lot-size" i]')
    if acreage_el:
        listing.acreage = parse_acreage(acreage_el.inner_text())
    else:
        # last-resort: scan full page text for "N acres"
        import re
        body_text = page.inner_text("body")
        m = re.search(r"([\d,.]+)\s*acres?", body_text, re.IGNORECASE)
        if m:
            listing.acreage = parse_acreage(m.group())

    # --- Agent contact info ---
    listing.agent_email = extract_mailto_email(page)
    listing.agent_phone = extract_tel_phone(page)

    # VERIFY: agent name/brokerage selectors — look for an "agent" or "broker"
    # info card on the listing detail page.
    agent_name_el = page.query_selector('[class*="agent-name" i], [class*="broker-name" i]')
    if agent_name_el:
        listing.agent_name = agent_name_el.inner_text().strip()

    brokerage_el = page.query_selector('[class*="brokerage" i], [class*="agency-name" i], [class*="office-name" i]')
    if brokerage_el:
        listing.brokerage = brokerage_el.inner_text().strip()

    if not listing.agent_email:
        # last resort: scan visible body text for any email address
        body_text = page.inner_text("body")
        listing.agent_email = find_first_email_in_text(body_text)

    if not listing.address or listing.acreage is None:
        logger.warning("Incomplete data for %s (address=%r, acreage=%r) — "
                        "selectors likely need adjustment for this page.",
                        url, listing.address, listing.acreage)

    return listing


def scrape(page, search_urls: list[str]) -> list[Listing]:
    all_listing_urls: list[str] = []
    for search_url in search_urls:
        urls = get_listing_urls_from_search(page, search_url, config.MAX_PAGES_PER_SEARCH)
        all_listing_urls.extend(urls)
        if len(all_listing_urls) >= config.MAX_LISTINGS_PER_RUN:
            break

    all_listing_urls = all_listing_urls[: config.MAX_LISTINGS_PER_RUN]
    logger.info("Collected %d total listing URLs to scrape.", len(all_listing_urls))

    results: list[Listing] = []
    for i, url in enumerate(all_listing_urls, 1):
        logger.info("[%d/%d] Scraping listing: %s", i, len(all_listing_urls), url)
        try:
            listing = scrape_listing_detail(page, url)
            if listing:
                results.append(listing)
        except Exception as e:
            # One blocked/broken listing must never kill the whole run.
            logger.error("Giving up on %s after retries: %s", url, e)
        polite_delay()

    return results
