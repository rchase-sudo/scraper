import csv
import os
from datetime import datetime

from dedup import AgentRecord
from models import Listing
from utils import setup_logger

logger = setup_logger("export")


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def write_raw_listings_csv(listings: list[Listing], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"listings_raw_{datetime.now():%Y%m%d_%H%M%S}.csv")

    fieldnames = ["source", "address", "city", "state", "price", "acreage",
                  "agent_name", "agent_email", "agent_phone", "brokerage",
                  "listing_url", "scraped_at"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for l in listings:
            writer.writerow({
                "source": l.source, "address": l.address, "city": l.city,
                "state": l.state, "price": l.price, "acreage": l.acreage,
                "agent_name": l.agent_name, "agent_email": l.agent_email,
                "agent_phone": l.agent_phone, "brokerage": l.brokerage,
                "listing_url": l.listing_url, "scraped_at": l.scraped_at,
            })

    logger.info("Wrote %d raw listings to %s", len(listings), path)
    return path


def write_instantly_csv(agent_records: list[AgentRecord], output_dir: str) -> str:
    """Mail-merge-ready CSV for Instantly.ai import.

    Columns map to {{merge_tags}} in Instantly campaign templates:
      email            -> required lead identifier
      first_name       -> {{first_name}}
      last_name        -> {{last_name}}
      company           -> {{company}}  (brokerage)
      phone            -> {{phone}}
      listing_address  -> {{listing_address}}
      listing_price    -> {{listing_price}}
      listing_acreage  -> {{listing_acreage}}
      listing_url      -> {{listing_url}}
      num_listings     -> {{num_listings}}
      other_listings   -> {{other_listings}}  (only populated when > 1 listing)

    Only agents with a usable email are included — Instantly requires email
    to import a lead.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"instantly_import_{datetime.now():%Y%m%d_%H%M%S}.csv")

    fieldnames = ["email", "first_name", "last_name", "company", "phone",
                  "listing_address", "listing_price", "listing_acreage",
                  "listing_url", "num_listings", "other_listings"]

    skipped_no_email = 0
    written = 0

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in agent_records:
            if not record.agent_email:
                skipped_no_email += 1
                continue
            primary = record.primary_listing
            first_name, last_name = _split_name(record.agent_name)
            writer.writerow({
                "email": record.agent_email,
                "first_name": first_name,
                "last_name": last_name,
                "company": record.brokerage,
                "phone": record.agent_phone,
                "listing_address": primary.address,
                "listing_price": f"{primary.price:,.0f}" if primary.price else "",
                "listing_acreage": primary.acreage,
                "listing_url": primary.listing_url,
                "num_listings": len(record.listings),
                "other_listings": record.other_listings_summary,
            })
            written += 1

    logger.info("Wrote %d agents to Instantly CSV at %s (%d skipped for missing email)",
                written, path, skipped_no_email)
    return path
