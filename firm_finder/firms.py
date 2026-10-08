"""Groups land listings into firms and collects every contact the listing data
exposes for each firm (listing agents, office email and phone)."""

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from common import (clean_email, firm_domain_from_email, normalize_firm_name,
                    phones_from_field, text_value)


@dataclass
class Contact:
    name: str = ""
    email: str = ""
    phones: list[str] = field(default_factory=list)
    role: str = ""          # "listing agent", "office", "website"
    source: str = ""        # "realtor.com listing", "<page url>"

    def key(self) -> str:
        return self.email or f"name:{self.name.lower().strip()}"


@dataclass
class Firm:
    key: str
    name: str
    land_listing_count: int = 0
    counties: set[str] = field(default_factory=set)
    office_phones: list[str] = field(default_factory=list)
    domain_votes: Counter = field(default_factory=Counter)
    listings: list[dict] = field(default_factory=list)
    contacts: dict[str, Contact] = field(default_factory=dict)
    # filled in by the website check
    website: str = ""
    website_land_hits: list[str] = field(default_factory=list)
    website_status: str = "not checked"
    # filled in by the DRE match
    dre_license_number: str = ""

    @property
    def domain(self) -> str:
        return self.domain_votes.most_common(1)[0][0] if self.domain_votes else ""

    @property
    def land_focus_score(self) -> int:
        """Rough ranking: land listings count most, website wording adds weight."""
        return self.land_listing_count * 10 + len(self.website_land_hits) * 5

    def add_contact(self, contact: Contact) -> None:
        """Adds a person, merging with an existing entry for the same email, or
        for the same name when one side has no email yet."""
        if not contact.email and not contact.name:
            return
        match = self.contacts.get(contact.email) if contact.email else None
        if match is None and contact.name:
            wanted = contact.name.lower().strip()
            match = next((c for c in self.contacts.values()
                          if c.name.lower().strip() == wanted
                          and (not c.email or not contact.email or c.email == contact.email)), None)
        if match is None:
            self.contacts[contact.key()] = contact
            return
        old_key = match.key()
        match.name = match.name or contact.name
        match.email = match.email or contact.email
        for phone in contact.phones:
            if phone not in match.phones:
                match.phones.append(phone)
        if old_key != match.key():
            del self.contacts[old_key]
            self.contacts[match.key()] = match

    def top_listings(self, n: int = 3) -> list[dict]:
        return sorted(self.listings, key=lambda l: l.get("price") or 0, reverse=True)[:n]


def _firm_identity(row) -> tuple[str, str]:
    """(key, display name) for the firm behind a listing. Office name is the
    best signal; broker name is the fallback; a lone agent becomes their own firm."""
    for column in ("office_name", "broker_name"):
        name = text_value(row.get(column))
        key = normalize_firm_name(name)
        if key:
            return key, name
    agent = text_value(row.get("agent_name"))
    email = clean_email(row.get("agent_email"))
    if email or agent:
        return f"agent:{email or agent.lower()}", agent or email
    return "", ""


def build_firms(listings: pd.DataFrame) -> list[Firm]:
    firms: dict[str, Firm] = {}

    for row in listings.to_dict("records"):
        key, name = _firm_identity(row)
        if not key:
            continue
        firm = firms.setdefault(key, Firm(key=key, name=name))
        firm.land_listing_count += 1
        county = text_value(row.get("county")) or text_value(row.get("search_county"))
        if county:
            firm.counties.add(county)

        price = row.get("list_price")
        lot_sqft = row.get("lot_sqft")
        firm.listings.append({
            "address": text_value(row.get("formatted_address")) or text_value(row.get("full_street_line")),
            "price": float(price) if pd.notna(price) else None,
            "acres": round(float(lot_sqft) / 43560, 2) if pd.notna(lot_sqft) and lot_sqft else None,
            "url": text_value(row.get("property_url")),
        })

        for phone in phones_from_field(row.get("office_phones")):
            if phone not in firm.office_phones:
                firm.office_phones.append(phone)

        office_email = clean_email(row.get("office_email"))
        if office_email:
            firm.add_contact(Contact(name=name, email=office_email, phones=list(firm.office_phones),
                                     role="office", source="realtor.com listing"))

        agent_email = clean_email(row.get("agent_email"))
        agent_name = text_value(row.get("agent_name"))
        firm.add_contact(Contact(name=agent_name, email=agent_email,
                                 phones=phones_from_field(row.get("agent_phones")),
                                 role="listing agent", source="realtor.com listing"))

        for email in (office_email, agent_email):
            domain = firm_domain_from_email(email)
            if domain:
                firm.domain_votes[domain] += 1

    return sorted(firms.values(), key=lambda f: f.land_listing_count, reverse=True)
