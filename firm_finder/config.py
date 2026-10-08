"""Settings for the California land-firm finder.

Everything here uses free sources only:
  - Realtor.com land listings (via the HomeHarvest library) -> which firms list land
  - Each firm's own public website -> land wording + staff emails
  - California DRE daily licensee file (optional) -> every licensed firm in CA
"""

STATE = "CA"

# All 58 California counties. Searching county by county keeps each query
# well under Realtor.com's per-search result cap.
CA_COUNTIES = [
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras", "Colusa", "Contra Costa",
    "Del Norte", "El Dorado", "Fresno", "Glenn", "Humboldt", "Imperial", "Inyo",
    "Kern", "Kings", "Lake", "Lassen", "Los Angeles", "Madera", "Marin", "Mariposa",
    "Mendocino", "Merced", "Modoc", "Mono", "Monterey", "Napa", "Nevada", "Orange",
    "Placer", "Plumas", "Riverside", "Sacramento", "San Benito", "San Bernardino",
    "San Diego", "San Francisco", "San Joaquin", "San Luis Obispo", "San Mateo",
    "Santa Barbara", "Santa Clara", "Santa Cruz", "Shasta", "Sierra", "Siskiyou",
    "Solano", "Sonoma", "Stanislaus", "Sutter", "Tehama", "Trinity", "Tulare",
    "Tuolumne", "Ventura", "Yolo", "Yuba",
]

# --- Listing pull (Realtor.com via HomeHarvest) ---
LISTING_PROPERTY_TYPES = ["land"]
DELAY_BETWEEN_COUNTIES = (8.0, 15.0)   # seconds, randomized
LISTING_RETRIES = 3
PROXY = None   # optional "http://user:pass@host:port" if Realtor.com starts blocking

# --- Firm website check ---
WEBSITE_PATHS = [
    "/", "/about", "/about-us", "/team", "/our-team", "/agents", "/our-agents",
    "/people", "/staff", "/contact", "/contact-us", "/land", "/services",
]
WEBSITE_DELAY = (1.5, 3.5)       # seconds between page requests on the same site
WEBSITE_TIMEOUT = 15
MAX_PAGES_PER_SITE = len(WEBSITE_PATHS)
USER_AGENT = "FormaFirmFinder/1.0 (business contact research)"

# Wording that shows a firm does land deals. Case-insensitive regexes.
LAND_PATTERNS = [
    r"vacant land", r"raw land", r"land sales?", r"land brokerage", r"land broker",
    r"land specialist", r"land investments?", r"land development", r"development land",
    r"development sites?", r"lots?\s*(?:&|and)\s*land", r"\bacreage\b",
    r"ranch(?:es)?\s*(?:&|and)\s*land", r"farm\s*(?:&|and)\s*ranch", r"entitlements?", r"land use", r"accredited land consultant", r"\bALC\b",
    r"realtors land institute",
]

# Free / personal mailbox domains: never treated as a firm's website domain.
FREEMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
    "me.com", "msn.com", "live.com", "comcast.net", "att.net", "sbcglobal.net",
    "verizon.net", "cox.net", "earthlink.net", "protonmail.com", "ymail.com",
    "mac.com", "pacbell.net", "charter.net",
}

# Domains that show up in emails but are platforms, not the firm itself.
PLATFORM_DOMAINS = {
    "realtor.com", "move.com", "zillow.com", "kw.com", "kwcommercial.com",
    "exprealty.com", "compass.com", "remax.net", "cbnorcal.com", "bhhscalifornia.com",
    "wix.com", "squarespace.com", "godaddy.com", "sentry.io", "example.com",
}
# Note: big franchise domains (kw.com, compass.com, ...) are skipped for the
# website check because their site describes the franchise, not the local
# office. Their agents are still kept as contacts from the listing data.

# Name keywords used to flag DRE-registered firms that look land-focused.
# Whole words only, so "Landmark" or "Branch" don't count.
LAND_NAME_KEYWORDS = [
    "land", "lands", "ranch", "ranches", "acre", "acres", "acreage", "farm", "farms",
    "lots", "development", "developments", "dirt",
]

OUTPUT_DIR = "output"
