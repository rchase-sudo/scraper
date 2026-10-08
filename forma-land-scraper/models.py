from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Listing:
    source: str
    listing_url: str
    address: str = ""
    city: str = ""
    state: str = ""
    price: float | None = None
    acreage: float | None = None
    agent_name: str = ""
    agent_email: str = ""
    agent_phone: str = ""
    brokerage: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def passes_acreage_filter(self, min_acres: float, max_acres: float) -> bool:
        if self.acreage is None:
            return False
        return min_acres <= self.acreage <= max_acres

    def has_contactable_agent(self) -> bool:
        return bool(self.agent_email)

    def dedup_key(self) -> str:
        if self.agent_email:
            return self.agent_email.strip().lower()
        # fall back to name+brokerage if no email was found, so we still group
        # multiple listings from the same agent even without an email on file
        if self.agent_name.strip():
            return f"{self.agent_name.strip().lower()}|{self.brokerage.strip().lower()}"
        # no email and no name: keep the listing on its own rather than merging
        # every unidentified listing into one fake "agent"
        return f"listing:{self.listing_url}"
