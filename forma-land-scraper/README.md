# Forma Designs — Land Listing Scraper

Scrapes vacant land listings, extracts listing-agent contact info, filters by
acreage, dedupes by agent, and exports a CSV ready to import into Instantly.ai.

## Before you run this

**Legal/ToS risk (read this).** LandWatch, Zillow, and LoopNet all actively
block automated access (bot detection, not just a ToS clause). This scraper
uses a real headless browser with stealth settings to get past that. LoopNet
and LandWatch are both owned by CoStar Group, which has a documented history
of suing scrapers and winning large judgments. This tool does not access any
private/gated data — everything it collects is publicly visible on listing
pages without logging in — but running it at any real scale still carries
real exposure (cease-and-desist, IP bans, potential civil suit). That risk
was flagged and knowingly accepted for this build; it doesn't go away by
building the tool. Keep volume modest and consider legal counsel if you plan
to scale this up.

**Not live-tested.** This was built without the ability to execute a live
request against the target sites in the session that wrote it (blocked by
the coding harness itself). The parsing logic in `scrapers/landwatch.py` is
based on general patterns (JSON-LD structured data, mailto:/tel: links, and
CSS-selector fallbacks marked `VERIFY`) — **not** confirmed against current
live HTML. **Your first run must be supervised:**

1. In `config.py`, set `HEADLESS = False`.
2. Paste one filtered LandWatch search-results URL into `SEARCH_URLS["landwatch"]`.
3. Run `python main.py --source landwatch` and watch the real browser window.
4. If it's not finding listings/agent info, open the same page in your own
   browser, right-click → Inspect on the relevant element, and fix the
   selector marked `VERIFY` in `scrapers/landwatch.py` to match.
5. Once it's reliably pulling correct data, set `HEADLESS = True` for normal runs.

## Setup

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## Configure

Edit `config.py`:
- `MIN_ACRES` / `MAX_ACRES` — currently 1–50.
- `SEARCH_URLS` — go to landwatch.com, apply your filters (acreage, state,
  property type) through their own site UI, copy the resulting URL, paste it
  in. You can add multiple URLs (e.g. one per state) to the list.
- `PROXIES` — optional but recommended for any real scale. A single
  residential IP will get rate-limited/blocked fast no matter how careful the
  stealth settings are. Rotating residential proxies are a separate paid
  service (e.g. Bright Data, Oxylabs, Smartproxy) — sign up and paste your
  proxy URLs here if you go that route.

## Run

```powershell
python main.py                     # all configured sources
python main.py --source landwatch  # just one source
python main.py --min-acres 5 --max-acres 40   # override config.py thresholds
```

Output lands in `output/`:
- `listings_raw_<timestamp>.csv` — every listing scraped, one row each.
- `instantly_import_<timestamp>.csv` — deduped by agent (multi-listing agents
  collapsed to one row, with their other listings summarized in a column),
  only agents with a found email, columns matching Instantly.ai merge tags:
  `email, first_name, last_name, company, phone, listing_address,
  listing_price, listing_acreage, listing_url, num_listings, other_listings`.

Import `instantly_import_*.csv` directly into an Instantly.ai campaign and
map the columns to your template's `{{merge_tags}}`.

## Scheduling

```powershell
.\schedule_task.ps1
```

Registers a Windows Task Scheduler job (default: weekly, Monday 6am). Edit
the trigger in `schedule_task.ps1` before running it if you want daily
instead. Remove it later with:

```powershell
Unregister-ScheduledTask -TaskName "FormaLandScraper" -Confirm:$false
```

## Expanding to Zillow / LoopNet

Only LandWatch is implemented so far (per "start with one source" — and
because all three block bots equally, LandWatch was picked as the most
land-listing-specific fit). To add another source once LandWatch is confirmed
working:

1. Copy `scrapers/landwatch.py` to `scrapers/zillow.py` (or `loopnet.py`).
2. Adjust the `VERIFY`-marked selectors and JSON-LD parsing for that site's
   actual markup (again — inspect real HTML first, in a supervised browser run).
3. Register it in `main.py`'s `SCRAPERS` dict.
4. Add its search URL(s) to `config.py`'s `SEARCH_URLS`.

Zillow in particular has materially stronger bot detection than LandWatch —
expect this to take more iteration, and consider proxies from the start.

## Anti-blocking behavior already built in

- Randomized delay between every request (`MIN_DELAY_SECONDS`–`MAX_DELAY_SECONDS`).
- Rotating user-agent and viewport fingerprint per browser session.
- Stealth JS injection to hide common headless-browser tells.
- Retry with exponential backoff on a blocked/failed request (`MAX_RETRIES`).
- A failure on any single listing is caught and logged, not fatal — the run
  continues to the next listing. Check `logs/` after each run for anything
  that needs attention.
- Optional proxy rotation (bring your own proxies).
