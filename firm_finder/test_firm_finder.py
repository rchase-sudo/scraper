"""Offline tests (no network): run with `python test_firm_finder.py`."""

import io
import os
import tempfile
import zipfile

import pandas as pd

import dre
import export
import website
from common import clean_email, firm_domain_from_email, normalize_firm_name, phones_from_field
from firms import build_firms
from supabase_push import to_crm_rows

LISTINGS = pd.DataFrame([
    {"property_id": "1", "formatted_address": "10 Ridge Rd, Auburn, CA", "list_price": 850000,
     "lot_sqft": 43560 * 12, "county": "Placer", "property_url": "https://realtor.com/1",
     "office_name": "Sierra Land Co., Inc.", "office_email": "info@sierralandco.com",
     "office_phones": [{"number": "530-555-0100", "type": "Office"}],
     "agent_name": "Dana Cruz", "agent_email": "dana@sierralandco.com",
     "agent_phones": [{"number": "5305550111"}]},
    {"property_id": "2", "formatted_address": "Hwy 49 Lot 4, Auburn, CA", "list_price": 1200000,
     "lot_sqft": 43560 * 30, "county": "Placer", "property_url": "https://realtor.com/2",
     "office_name": "Sierra Land Co", "office_email": None, "office_phones": None,
     "agent_name": "Dana Cruz", "agent_email": None, "agent_phones": ["(530) 555-0111"]},
    {"property_id": "3", "formatted_address": "5 Oak Ln, Placerville, CA", "list_price": 300000,
     "lot_sqft": 43560 * 2, "county": "El Dorado", "property_url": "https://realtor.com/3",
     "office_name": "Sierra Land Co LLC", "office_email": None, "office_phones": None,
     "agent_name": "Lee Park", "agent_email": "leepark.re@gmail.com", "agent_phones": None},
    {"property_id": "4", "formatted_address": "Desert Parcel, Barstow, CA", "list_price": float("nan"),
     "lot_sqft": float("nan"), "county": "San Bernardino", "property_url": "https://realtor.com/4",
     "office_name": None, "broker_name": None, "office_email": None, "office_phones": None,
     "agent_name": "Sam Solo", "agent_email": "sam@kw.com", "agent_phones": None},
])


def test_helpers():
    assert clean_email("mailto:Dana@SierraLandCo.com?subject=hi") == "dana@sierralandco.com"
    assert clean_email("logo@2x.png") == ""
    assert clean_email("noreply@firm.com") == ""
    assert firm_domain_from_email("x@gmail.com") == ""
    assert firm_domain_from_email("sam@kw.com") == ""          # franchise domain
    assert firm_domain_from_email("a@sierralandco.com") == "sierralandco.com"
    assert phones_from_field([{"number": "1-530-555-0100"}, "530.555.0100"]) == ["(530) 555-0100"]
    assert phones_from_field(float("nan")) == []
    assert normalize_firm_name("Sierra Land Co., Inc.") == normalize_firm_name("Sierra Land Co LLC")


def test_build_firms():
    firms = build_firms(LISTINGS)
    names = {f.key: f for f in firms}
    sierra = names[normalize_firm_name("Sierra Land Co")]
    assert sierra.land_listing_count == 3, "Inc/LLC/plain spellings should merge into one firm"
    assert sierra.counties == {"Placer", "El Dorado"}
    assert sierra.domain == "sierralandco.com"
    assert sierra.office_phones == ["(530) 555-0100"]
    emails = {c.email for c in sierra.contacts.values()}
    assert emails == {"info@sierralandco.com", "dana@sierralandco.com", "leepark.re@gmail.com"}
    dana = sierra.contacts["dana@sierralandco.com"]
    assert dana.phones == ["(530) 555-0111"], "same agent on two listings is one contact"
    assert sierra.top_listings(1)[0]["price"] == 1200000
    solo = [f for f in firms if f.key.startswith("agent:")]
    assert len(solo) == 1 and solo[0].domain == "", "lone agent with franchise email -> own firm, no site"


PAGE = """<html><head><script>var x='junk@tracker.io'</script></head><body>
<h1>Sierra Land Co</h1><p>We specialize in vacant land and ranch & land sales across the foothills.</p>
<a href="mailto:dana@sierralandco.com">Dana Cruz</a>
<a href="mailto:office@sierralandco.com">Email us</a>
<p>Contact Lee: leepark.re@gmail.com. Site by webguy@designshop.com</p></body></html>"""


def test_page_parsing():
    text, mailtos = website.parse_page(PAGE)
    assert "junk@tracker.io" not in text, "script contents must be ignored"
    hits = website.land_hits(text)
    assert any("vacant land" in h for h in hits)
    contacts = {c.email: c for c in website.emails_from_page(text, mailtos, "sierralandco.com")}
    assert set(contacts) == {"dana@sierralandco.com", "office@sierralandco.com", "leepark.re@gmail.com"}
    assert contacts["dana@sierralandco.com"].name == "Dana Cruz"
    assert contacts["office@sierralandco.com"].name == "", "'Email us' is not a person's name"


class _Resp:
    def __init__(self, url, status=200, text="", ctype="text/html"):
        self.url, self.status_code, self.text = url, status, text
        self.headers = {"content-type": ctype}


class _FakeSession:
    """robots.txt blocks /team; every other page returns PAGE."""
    def __init__(self):
        self.requested = []

    def get(self, url, **_):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            return _Resp(url, text="User-agent: *\nDisallow: /team", ctype="text/plain")
        return _Resp(url, text=PAGE)


def test_website_check_respects_robots():
    website.time.sleep = lambda *_: None          # no waiting in tests
    firm = build_firms(LISTINGS)[0]
    session = _FakeSession()
    website.check_firm_website(firm, session)
    assert not any(u.endswith("/team") for u in session.requested), "robots.txt disallow ignored"
    assert firm.website == "https://sierralandco.com"
    assert firm.website_land_hits
    assert "office@sierralandco.com" in firm.contacts
    assert firm.contacts["dana@sierralandco.com"].name == "Dana Cruz"


def test_dre_loading():
    rows = [
        ["N", "SIERRA LAND CO INC", "", "", "01111111", "Corporation", "Licensed", "", "", "", "", "", "", "", "",
         "1 Main St", "", "Auburn", "CA", "95603", "", "", "Placer", "N", "Y"],
        ["N", "Smith", "John", "", "02222222", "Broker", "Licensed", "", "", "", "", "", "", "", "",
         "2 Elm", "", "Fresno", "CA", "93701", "", "", "Fresno", "N", "Y"],
        ["N", "Jones", "Amy", "", "03333333", "Broker", "Licensed", "", "", "", "01111111", "", "", "", "Corporation",
         "", "", "", "CA", "", "", "", "", "N", "Y"],
        ["N", "OLD RANCH REALTY", "", "", "04444444", "Corporation", "Expired", "", "", "", "", "", "", "", "",
         "", "", "", "CA", "", "", "", "", "N", "Y"],
        ["N", "Main Branch Realty", "", "", "05555555", "Corporation", "Licensed", "", "", "", "", "", "", "", "",
         "", "", "", "CA", "", "", "", "", "N", "Y"],
        ["N", "Smith", "Jane", "", "06666666", "Salesperson", "Licensed", "", "", "", "02222222", "", "", "", "Broker",
         "", "", "", "CA", "", "", "", "", "N", "Y"],
    ]
    csv_text = "\n".join(",".join(r) for r in rows)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "CurrList.zip")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("CurrList.csv", csv_text)
        firms = dre.firms_from_licenses(dre.load(path))
    names = dict(zip(firms["firm_name"], firms["land_in_name"]))
    assert names == {"SIERRA LAND CO INC": True, "John Smith": False, "Main Branch Realty": False}, names


def test_crm_rows_skip_existing():
    contacts = export.contacts_table(build_firms(LISTINGS))
    rows = to_crm_rows(contacts, emails={"dana@sierralandco.com"}, phones=set())
    emails = {r["email"] for r in rows}
    assert "dana@sierralandco.com" not in emails, "already in CRM"
    assert "info@sierralandco.com" in emails
    assert all(r["campaign_active"] is False and r["status"] == "lead" for r in rows)


def test_export_files():
    firms = build_firms(LISTINGS)
    with tempfile.TemporaryDirectory() as tmp:
        paths = export.write_all(tmp, LISTINGS, firms)
        instantly = pd.read_csv(paths["instantly"]).fillna("")
        assert instantly["email"].is_unique and (instantly["email"] != "").all()
        top = pd.read_csv(paths["firms"]).iloc[0]
        assert top["firm_name"].startswith("Sierra Land") and top["land_listings"] == 3


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\nALL {len(tests)} TESTS PASSED")
