"""
Central configuration for the Forma Designs land-listing scraper.

IMPORTANT — read before first run:
This was built without the ability to execute a live test against the target
sites (blocked by the harness that built it), so selectors/parsing logic are
based on general knowledge of how these sites tend to be structured, not
verified against current live HTML. Run the FIRST pass with HEADLESS = False
and LIMIT set low (e.g. 5) so you can watch it in a real browser window and
confirm it's actually finding/parsing listings correctly before trusting the
output or scaling up.
"""

# --- Filtering ---
MIN_ACRES = 1        # excludes postage-stamp residential lots
MAX_ACRES = 50        # per your "max of 50 acres" answer

# --- Search scope ---
# Go to the source site, apply your filters (acreage, nationwide/state,
# "land"/"vacant land" property type) through their own UI, then paste the
# resulting search-results URL(s) here. This avoids guessing at each site's
# query-parameter scheme, which changes without notice.
SEARCH_URLS = {
    "landwatch": [
        # "https://www.landwatch.com/..."   <- paste your filtered search URL(s) here
    ],
    "zillow": [
        # "https://www.zillow.com/..."
    ],
    "loopnet": [
        # "https://www.loopnet.com/..."
    ],
}

MAX_PAGES_PER_SEARCH = 10   # pagination safety cap per search URL
MAX_LISTINGS_PER_RUN = 500  # overall safety cap for a single run

# --- Politeness / anti-block behavior ---
HEADLESS = True              # set False for the first supervised run
MIN_DELAY_SECONDS = 4.0      # randomized delay range between requests
MAX_DELAY_SECONDS = 11.0
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 8.0   # exponential backoff base on retry

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

VIEWPORTS = [
    {"width": 1366, "height": 900},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
]

# --- Optional proxy support ---
# If you have residential/rotating proxies (recommended for any real scale —
# a single residential IP hammering these sites will get blocked fast
# regardless of stealth settings), fill this in. Format: "http://user:pass@host:port"
PROXIES = [
    # "http://user:pass@proxy1.example.com:8000",
]

# --- Output ---
OUTPUT_DIR = "output"
LOG_DIR = "logs"
