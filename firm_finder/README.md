# California Land-Firm Finder

Finds every California real estate firm that does land deals and collects as
many contacts per firm as free sources allow. Output is ranked so the firms
whose bread and butter is land come first.

## How a firm qualifies

A firm makes the list if **either**:
- it has **1 or more active land listing** on Realtor.com in California, or
- its **own website talks about land deals** (vacant land, land sales,
  acreage, development sites, farm & ranch, entitlements, ALC/RLI, ...).

Firms are ranked by `land_focus_score` = land listings × 10 + website land
mentions × 5.

## Where the data comes from (all free)

| Step | Source | What it gives |
|---|---|---|
| 1 | Realtor.com land listings, all 58 counties (HomeHarvest library) | Firms with land listings, listing agents, agent and office emails and phones |
| 2 | Each firm's own website: home, about, team, agents, contact, land, services pages | Land wording, extra staff emails |
| 3 | *(optional)* CA Department of Real Estate daily licensee file | Every licensed firm in CA, flagged when the name says land/ranch/acreage |

**Limits to know:**
- The DRE file has no emails, phones or websites. Firms that appear only
  there (no land listings) get no contacts and no website check. They're in
  `all_ca_firms_dre.csv` as a master list.
- A firm's website is only known when one of its staff uses a firm email
  address (e.g. `dana@sierralandco.com`). Agents on gmail, or on big franchise
  domains like `kw.com` / `compass.com`, are still kept as contacts, but their
  office website isn't checked.
- The website check obeys each site's robots.txt and waits 1.5–3.5 s between
  pages.

## Setup

```powershell
cd firm_finder
pip install -r requirements.txt
```

## Run on GitHub (no setup on your computer)

1. Repo → **Actions** tab → **CA land-firm finder** → **Run workflow**.
2. Pick counties (comma-separated, or `all`), whether to check websites, the
   DRE list, and the CRM option (`none`, `dry-run`, `push`).
3. When it finishes, open the run: the summary shows the counts, and the CSVs
   download under **Artifacts** (kept 30 days).

For the CRM options, add two repo secrets first (repo → Settings → Secrets
and variables → Actions): `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

To run it automatically, uncomment the `schedule:` lines in
`.github/workflows/firm-finder.yml`.

## Run on your computer

```powershell
python run.py --counties "Placer" "El Dorado"   # test on 2 counties first
python run.py                                   # all 58 counties (several hours)
python run.py --dre                             # also pull the DRE master list
python run.py --skip-websites                   # listings only, much faster
```

Output lands in `output/<timestamp>/`:

| File | Contents |
|---|---|
| `land_firms.csv` | One row per firm, ranked: land listings, counties, website, land wording found, phones, contact counts |
| `land_firm_contacts.csv` | Every contact found, one row each, with firm and top-listing details |
| `instantly_import.csv` | Contacts with an email, deduped, columns ready for Instantly merge tags |
| `land_listings.csv` | Every raw land listing pulled |
| `all_ca_firms_dre.csv` | *(with `--dre`)* every licensed CA firm, with land-name flag |

## Add contacts to the Supabase CRM

Set two environment variables (Supabase → Project Settings → API). Never
commit the service role key.

```powershell
$env:SUPABASE_URL = "https://<project-ref>.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role key>"
python run.py --counties "Placer" --crm-dry-run   # counts what would be added
python run.py --counties "Placer" --push          # actually adds them
```

New contacts go into `contacts` as `status = lead`, `company_type =
real_estate`, `source = firm finder`, tagged `land-firm`. Anyone already in
the CRM (same email, or same phone when there's no email) is skipped.
`campaign_active` stays `false`, so nobody is auto-called until you start a
campaign on them.

## If Realtor.com starts blocking

Errors on many counties in a row usually mean rate limiting. Wait a few hours,
run fewer counties at a time, or set `PROXY` in `config.py`.

## Tests

```powershell
python test_firm_finder.py    # offline, uses fake data
```
