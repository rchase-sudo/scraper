"""Extraction helpers shared across site-specific scrapers.

These are deliberately layered from most-robust to least-robust:
  1. JSON-LD structured data (schema.org) — survives redesigns, many real
     estate sites embed this for SEO.
  2. Framework hydration JSON (e.g. Next.js __NEXT_DATA__) — also survives
     styling changes, breaks only on major framework migrations.
  3. mailto:/tel: links anywhere on the page — agent contact info is almost
     always exposed this way regardless of CSS class naming.
  4. Raw CSS selectors — most brittle, last resort. Marked VERIFY below;
     confirm against live HTML (view-source or browser devtools) before
     relying on these.
"""

import json
import re

from utils import normalize_email, normalize_phone


def extract_json_ld(page) -> list[dict]:
    """Returns all parsed JSON-LD blocks on the page."""
    blocks = []
    scripts = page.query_selector_all('script[type="application/ld+json"]')
    for s in scripts:
        try:
            content = s.inner_text()
            data = json.loads(content)
            if isinstance(data, list):
                blocks.extend(data)
            else:
                blocks.append(data)
        except (json.JSONDecodeError, Exception):  # noqa: BLE001
            continue
    return blocks


def extract_next_data(page) -> dict | None:
    """Returns parsed __NEXT_DATA__ JSON if the page is a Next.js app."""
    el = page.query_selector("script#__NEXT_DATA__")
    if not el:
        return None
    try:
        return json.loads(el.inner_text())
    except json.JSONDecodeError:
        return None


def extract_mailto_email(page) -> str:
    el = page.query_selector('a[href^="mailto:"]')
    if not el:
        return ""
    href = el.get_attribute("href") or ""
    return normalize_email(href.replace("mailto:", ""))


def extract_tel_phone(page) -> str:
    el = page.query_selector('a[href^="tel:"]')
    if not el:
        return ""
    href = el.get_attribute("href") or ""
    return normalize_phone(href.replace("tel:", ""))


def find_first_email_in_text(text: str) -> str:
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text or "")
    return match.group().lower() if match else ""
