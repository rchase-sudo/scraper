"""Writes the results to CSV files."""

import os

import pandas as pd

from firms import Firm


def _split_name(full: str) -> tuple[str, str]:
    parts = (full or "").split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def _money(value) -> str:
    return f"${value:,.0f}" if value else ""


def firms_table(firms: list[Firm]) -> pd.DataFrame:
    rows = []
    for rank, firm in enumerate(sorted(firms, key=lambda f: f.land_focus_score, reverse=True), 1):
        top = firm.top_listings(3)
        rows.append({
            "rank": rank,
            "firm_name": firm.name,
            "land_listings": firm.land_listing_count,
            "counties": ", ".join(sorted(firm.counties)),
            "website": firm.website or (f"https://{firm.domain}" if firm.domain else ""),
            "website_status": firm.website_status,
            "website_land_mentions": len(firm.website_land_hits),
            "website_land_examples": " | ".join(firm.website_land_hits[:3]),
            "office_phones": ", ".join(firm.office_phones),
            "contacts": len(firm.contacts),
            "contacts_with_email": sum(1 for c in firm.contacts.values() if c.email),
            "dre_license": firm.dre_license_number,
            "land_focus_score": firm.land_focus_score,
            "top_listings": "; ".join(
                f"{l['address']} ({l['acres']} ac, {_money(l['price'])})" for l in top),
        })
    return pd.DataFrame(rows)


def contacts_table(firms: list[Firm]) -> pd.DataFrame:
    rows = []
    for firm in firms:
        top = firm.top_listings(1)
        listing = top[0] if top else {}
        for contact in firm.contacts.values():
            first, last = _split_name(contact.name if contact.role != "office" else "")
            rows.append({
                "email": contact.email,
                "first_name": first,
                "last_name": last,
                "name": contact.name,
                "role": contact.role,
                "phone": contact.phones[0] if contact.phones else "",
                "other_phones": ", ".join(contact.phones[1:]),
                "company": firm.name,
                "company_website": firm.website or (f"https://{firm.domain}" if firm.domain else ""),
                "firm_land_listings": firm.land_listing_count,
                "firm_land_focus_score": firm.land_focus_score,
                "listing_address": listing.get("address", ""),
                "listing_price": _money(listing.get("price")),
                "listing_acreage": listing.get("acres") or "",
                "listing_url": listing.get("url", ""),
                "found_on": contact.source,
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["firm_land_focus_score", "company"], ascending=[False, True])
    return df


def write_all(out_dir: str, listings: pd.DataFrame, firms: list[Firm],
              dre_firms: pd.DataFrame | None = None) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = {}

    keep = [c for c in listings.columns if c not in ("alt_photos", "nearby_schools", "tax_history")]
    paths["listings"] = os.path.join(out_dir, "land_listings.csv")
    listings[keep].to_csv(paths["listings"], index=False)

    paths["firms"] = os.path.join(out_dir, "land_firms.csv")
    firms_table(firms).to_csv(paths["firms"], index=False)

    contacts = contacts_table(firms)
    paths["contacts"] = os.path.join(out_dir, "land_firm_contacts.csv")
    contacts.to_csv(paths["contacts"], index=False)

    paths["instantly"] = os.path.join(out_dir, "instantly_import.csv")
    if contacts.empty:
        contacts.to_csv(paths["instantly"], index=False)
    else:
        contacts[contacts["email"] != ""].drop_duplicates("email").to_csv(paths["instantly"], index=False)

    if dre_firms is not None and not dre_firms.empty:
        cols = ["firm_name", "Lic_Number", "Lic_Type", "Address_1", "City", "Zip_Code",
                "County_name", "land_in_name", "land_listings", "on_land_firm_list"]
        paths["dre"] = os.path.join(out_dir, "all_ca_firms_dre.csv")
        dre_firms[[c for c in cols if c in dre_firms.columns]].to_csv(paths["dre"], index=False)

    return paths
