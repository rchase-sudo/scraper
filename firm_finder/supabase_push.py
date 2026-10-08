"""Adds new contacts to the Supabase CRM `contacts` table.

Needs two environment variables (never commit these):
    SUPABASE_URL               e.g. https://<project-ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY  Project Settings -> API -> service_role key

Skips anyone already in the CRM (matched by email, then by phone). New rows
go in as status 'lead' with campaign_active left false, so nothing gets
auto-called until you start a campaign on them yourself.
"""

import os

import pandas as pd
import requests

from common import clean_phone, setup_logger

logger = setup_logger("supabase")

BATCH_SIZE = 500


def _client() -> tuple[str, dict]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to push to the CRM.")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    return f"{url}/rest/v1/contacts", headers


def existing_keys(endpoint: str, headers: dict) -> tuple[set[str], set[str]]:
    emails, phones = set(), set()
    offset = 0
    while True:
        resp = requests.get(endpoint, headers={**headers, "Range": f"{offset}-{offset + 999}"},
                            params={"select": "email,phone"}, timeout=60)
        resp.raise_for_status()
        rows = resp.json()
        for row in rows:
            if row.get("email"):
                emails.add(row["email"].strip().lower())
            phone = clean_phone(row.get("phone"))
            if phone:
                phones.add(phone)
        if len(rows) < 1000:
            return emails, phones
        offset += 1000


def to_crm_rows(contacts: pd.DataFrame, emails: set[str], phones: set[str]) -> list[dict]:
    rows, seen = [], set()
    for c in contacts.to_dict("records"):
        email = (c.get("email") or "").lower()
        phone = c.get("phone") or ""
        if not email and not phone:
            continue
        key = email or phone
        if key in seen or (email and email in emails) or (not email and phone in phones):
            continue
        seen.add(key)
        notes = [f"Firm land listings: {c['firm_land_listings']}"]
        if c.get("listing_url"):
            notes.append(f"Top listing: {c['listing_address']} {c['listing_price']} "
                         f"({c['listing_acreage']} ac) {c['listing_url']}")
        if c.get("found_on"):
            notes.append(f"Contact found on: {c['found_on']}")
        rows.append({
            "name": c.get("name") or c.get("company") or email,
            "company": c.get("company") or None,
            "email": email or None,
            "phone": phone or None,
            "website": c.get("company_website") or None,
            "status": "lead",
            "source": "firm finder",
            "company_type": "real_estate",
            "campaign_active": False,
            "listing_address": c.get("listing_address") or None,
            "tags": ["land-firm", "CA", c.get("role") or "contact"],
            "notes": " | ".join(notes),
        })
    return rows


def push(contacts: pd.DataFrame, dry_run: bool = True) -> int:
    endpoint, headers = _client()
    emails, phones = existing_keys(endpoint, headers)
    rows = to_crm_rows(contacts, emails, phones)
    logger.info("%d new contacts to add (%d already in CRM or duplicates skipped).",
                len(rows), len(contacts) - len(rows))
    if dry_run:
        logger.info("Dry run: nothing written. Re-run with --push to insert.")
        return len(rows)
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        resp = requests.post(endpoint, headers={**headers, "Prefer": "return=minimal"},
                             json=batch, timeout=120)
        resp.raise_for_status()
        logger.info("Inserted %d/%d", min(start + BATCH_SIZE, len(rows)), len(rows))
    return len(rows)
