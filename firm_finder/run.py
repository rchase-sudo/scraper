"""California land-firm finder.

Finds real estate firms that do land deals and collects as many of their
contacts as free sources allow:

  1. Pull every active land listing in California from Realtor.com.
     Any firm with 1+ land listing is on the list.
  2. Check each firm's own website for land wording and staff emails.
  3. (Optional) Load the DRE licensee file: every licensed firm in CA,
     flagged when the name says land/ranch/acreage.
  4. Write CSVs, and optionally add new contacts to the Supabase CRM.

Usage (from inside firm_finder/):
    python run.py                                   # all 58 counties
    python run.py --counties "Placer" "El Dorado"   # a few counties
    python run.py --dre                             # also download the DRE file
    python run.py --dre-file CurrList.zip           # use a DRE file you already have
    python run.py --crm-dry-run                     # show what would be added to the CRM
    python run.py --push                            # add new contacts to the CRM
"""

import argparse
import os
from datetime import datetime

import config
import dre
import export
from common import setup_logger
from firms import build_firms
from listings import pull_land_listings
from website import check_websites

logger = setup_logger("run")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find California firms that do land deals.")
    parser.add_argument("--counties", nargs="+", default=config.CA_COUNTIES,
                        help="County names (default: all 58)")
    parser.add_argument("--skip-websites", action="store_true", help="Skip the firm website check")
    parser.add_argument("--dre", action="store_true", help="Download today's DRE licensee file")
    parser.add_argument("--dre-file", help="Path to a DRE CurrList.zip you already downloaded")
    parser.add_argument("--crm-dry-run", action="store_true",
                        help="Count new CRM contacts without writing anything")
    parser.add_argument("--push", action="store_true", help="Insert new contacts into the CRM")
    args = parser.parse_args()

    out_dir = os.path.join(config.OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))

    listings = pull_land_listings(args.counties)
    if listings.empty:
        logger.error("No land listings came back. Realtor.com may be blocking requests; "
                     "try again later or set config.PROXY.")
        raise SystemExit(1)   # non-zero so a scheduled/CI run shows as failed
    firms = build_firms(listings)
    logger.info("%d land listings -> %d firms with 1+ land listing", len(listings), len(firms))

    if not args.skip_websites:
        check_websites(firms)

    dre_firms = None
    if args.dre or args.dre_file:
        path = args.dre_file or dre.download(out_dir)
        dre_firms = dre.firms_from_licenses(dre.load(path))
        by_key = {f.key: f for f in firms}
        dre_firms["land_listings"] = dre_firms["firm_key"].map(
            lambda k: by_key[k].land_listing_count if k in by_key else 0)
        dre_firms["on_land_firm_list"] = dre_firms["land_listings"] > 0
        for row in dre_firms[dre_firms["on_land_firm_list"]].itertuples():
            by_key[row.firm_key].dre_license_number = row.Lic_Number

    paths = export.write_all(out_dir, listings, firms, dre_firms)
    contacts = export.contacts_table(firms)
    with_email = int((contacts["email"] != "").sum()) if not contacts.empty else 0
    land_site = sum(1 for f in firms if f.website_land_hits)

    print(f"\nDone. {len(listings)} land listings, {len(firms)} firms "
          f"({land_site} also mention land on their website), "
          f"{len(contacts)} contacts ({with_email} with email).")
    for name, path in paths.items():
        print(f"  {name:10s} {path}")

    if args.push or args.crm_dry_run:
        from supabase_push import push
        added = push(contacts, dry_run=not args.push)
        print(f"  CRM: {added} new contacts {'added' if args.push else 'would be added (dry run)'}")


if __name__ == "__main__":
    main()
