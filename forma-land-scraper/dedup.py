from dataclasses import dataclass, field

from models import Listing


@dataclass
class AgentRecord:
    agent_name: str
    agent_email: str
    agent_phone: str
    brokerage: str
    listings: list[Listing] = field(default_factory=list)

    @property
    def primary_listing(self) -> Listing:
        """Highest-price listing is used for the main mail-merge fields —
        keeps the outreach anchored to their most valuable parcel."""
        return max(self.listings, key=lambda l: (l.price or 0))

    @property
    def other_listings_summary(self) -> str:
        others = [l for l in self.listings if l is not self.primary_listing]
        return "; ".join(f"{l.address} ({l.acreage} ac, ${l.price:,.0f})" if l.price else f"{l.address} ({l.acreage} ac)"
                          for l in others)


def dedupe_by_agent(listings: list[Listing]) -> list[AgentRecord]:
    """Groups listings by agent (email if available, else name+brokerage),
    keeping every listing so multi-listing agents aren't lost."""
    by_key: dict[str, AgentRecord] = {}

    for listing in listings:
        key = listing.dedup_key()
        if key not in by_key:
            by_key[key] = AgentRecord(
                agent_name=listing.agent_name,
                agent_email=listing.agent_email,
                agent_phone=listing.agent_phone,
                brokerage=listing.brokerage,
                listings=[],
            )
        record = by_key[key]
        record.listings.append(listing)
        # backfill contact fields if an earlier listing for this agent was missing them
        record.agent_name = record.agent_name or listing.agent_name
        record.agent_email = record.agent_email or listing.agent_email
        record.agent_phone = record.agent_phone or listing.agent_phone
        record.brokerage = record.brokerage or listing.brokerage

    return list(by_key.values())
