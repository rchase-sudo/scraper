"""Standalone test of dedup + CSV export using fake data (no network)."""
from models import Listing
from dedup import dedupe_by_agent
from export_csv import write_raw_listings_csv, write_instantly_csv

fake_listings = [
    Listing(source="landwatch", listing_url="https://example.com/1",
            address="123 Old Farm Rd", city="Wolfeboro", state="NH",
            price=250000, acreage=12.5, agent_name="Jane Smith",
            agent_email="jane@brokerco.com", agent_phone="6035551212",
            brokerage="Broker Co"),
    Listing(source="landwatch", listing_url="https://example.com/2",
            address="45 River Rd", city="Conway", state="NH",
            price=410000, acreage=30.0, agent_name="Jane Smith",
            agent_email="jane@brokerco.com", agent_phone="6035551212",
            brokerage="Broker Co"),
    Listing(source="landwatch", listing_url="https://example.com/3",
            address="9 Ridge Ln", city="Bangor", state="ME",
            price=90000, acreage=3.0, agent_name="Tom Lee",
            agent_email="", agent_phone="", brokerage="Lee Realty"),  # no email -> excluded from instantly csv
    Listing(source="landwatch", listing_url="https://example.com/4",
            address="1 Lake Shore Dr", city="Augusta", state="ME",
            price=None, acreage=75.0, agent_name="Big Lot", brokerage="X"),  # fails acreage filter
]

filtered = [l for l in fake_listings if l.passes_acreage_filter(1, 50)]
print(f"Filtered: {len(filtered)}/{len(fake_listings)} pass 1-50 acre range")
assert len(filtered) == 3, "acreage filter should drop the 75-acre listing"

agents = dedupe_by_agent(filtered)
print(f"Deduped to {len(agents)} agents")
assert len(agents) == 2, "Jane Smith's two listings should collapse to one agent record"

jane = next(a for a in agents if a.agent_email == "jane@brokerco.com")
assert len(jane.listings) == 2
assert jane.primary_listing.address == "45 River Rd"  # higher price
print("Jane's primary listing correctly picked as higher-priced one:", jane.primary_listing.address)
print("Jane's other_listings_summary:", jane.other_listings_summary)

raw_path = write_raw_listings_csv(filtered, "output")
instantly_path = write_instantly_csv(agents, "output")

with open(instantly_path, encoding="utf-8") as f:
    content = f.read()
print("\n--- instantly CSV content ---")
print(content)

assert "jane@brokerco.com" in content
assert "tom" not in content.lower() and "lee@" not in content.lower(), "Tom Lee has no email, should be excluded"
assert content.count("\n") == 2 or content.strip().count("\n") + 1 == 2, "should have header + 1 data row (only jane has email)"

# Price parser: a "k"/"m" elsewhere in the text must not multiply the price.
from utils import parse_price
assert parse_price("$250,000 - make an offer") == 250000
assert parse_price("Price: $89,900 (Motivated seller!)") == 89900
assert parse_price("$1.2M") == 1_200_000 and parse_price("$450K") == 450_000

# Listings with no agent email and no agent name must not merge into one "agent".
unnamed = [Listing(source="landwatch", listing_url=f"https://example.com/u{i}", acreage=5.0) for i in range(3)]
assert len(dedupe_by_agent(unnamed)) == 3

print("\nALL ASSERTIONS PASSED")
