"""Loads the California Department of Real Estate's daily public licensee file
(free download) and turns it into a list of every licensed firm in the state.

Field layout comes from DRE form RE 776. The file has names, license numbers
and mailing addresses only: no emails, phones or websites.
"""

import io
import os
import zipfile

import pandas as pd
import requests

from common import normalize_firm_name, setup_logger, text_value
import config

logger = setup_logger("dre")

DRE_URL = "https://secure.dre.ca.gov/datafile/CurrList.zip"
RE776_COLUMNS = [
    "Multiple_License_Ind", "LastName_Primary", "FirstName_Secondary", "Name_Suffix",
    "Lic_Number", "Lic_Type", "Lic_Status", "Lic_Effective_Date", "Lic_Expiration_Date",
    "Original_date_of_license", "Related_Lic_Number", "Related_LastName_Primary",
    "Related_FirstName_Secondary", "Related_Name_Suffix", "Related_Lic_Type",
    "Address_1", "Address_2", "City", "State", "Zip_Code", "Foreign_Nation",
    "Foreign_Postal_Info", "County_name", "Restricted_Flag", "Ethics_and_Agency_Ind",
]
_INACTIVE_WORDS = ("EXPIRED", "REVOKED", "SURRENDER", "CANCEL", "DECEASED", "SUSPEND", "DENIED")


def download(dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "CurrList.zip")
    logger.info("Downloading DRE licensee file from %s", DRE_URL)
    with requests.get(DRE_URL, stream=True, timeout=120,
                      headers={"User-Agent": config.USER_AGENT}) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
    return path


def _read_member(name: str, data: bytes) -> pd.DataFrame:
    lower = name.lower()
    if lower.endswith((".xls", ".xlsx")):
        return pd.read_excel(io.BytesIO(data), dtype=str)
    text = data.decode("latin-1")
    first_line = text.splitlines()[0] if text else ""
    sep = max([",", "\t", "|", ";"], key=first_line.count)
    has_header = "lic_number" in first_line.lower()
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=str,
                       header=0 if has_header else None,
                       names=None if has_header else RE776_COLUMNS,
                       on_bad_lines="skip", engine="python")


def load(path: str) -> pd.DataFrame:
    """Reads CurrList.zip (or an already-extracted .xls/.csv/.txt)."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            frames = [_read_member(n, zf.read(n)) for n in zf.namelist()
                      if n.lower().endswith((".xls", ".xlsx", ".csv", ".txt"))]
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    else:
        with open(path, "rb") as f:
            df = _read_member(path, f.read())
    df.columns = [str(c).strip() for c in df.columns]
    logger.info("Loaded %d DRE license records", len(df))
    return df


def firms_from_licenses(df: pd.DataFrame) -> pd.DataFrame:
    """Every active licensed firm: all corporations, plus individual brokers
    who aren't tied to another license (i.e. likely running their own shop).
    Brokers working under another broker show a Related_Lic_Number and are
    left out, since they're agents of a firm already on the list."""
    if df.empty:
        return df
    lic_type = df["Lic_Type"].fillna("").str.upper()
    status = df["Lic_Status"].fillna("").str.upper()
    active = ~status.apply(lambda s: any(w in s for w in _INACTIVE_WORDS))
    related = df["Related_Lic_Number"].fillna("").str.strip()

    is_corp = lic_type.str.contains("CORP")
    is_independent_broker = lic_type.str.contains("BROKER") & ~lic_type.str.contains("ASSOC") & (related == "")
    firms = df[active & (is_corp | is_independent_broker)].copy()

    def display_name(row) -> str:
        if "CORP" in text_value(row["Lic_Type"]).upper():
            return text_value(row["LastName_Primary"])
        return " ".join(p for p in (text_value(row["FirstName_Secondary"]),
                                    text_value(row["LastName_Primary"]),
                                    text_value(row["Name_Suffix"])) if p)

    firms["firm_name"] = firms.apply(display_name, axis=1)
    firms["firm_key"] = firms["firm_name"].map(normalize_firm_name)
    keywords = set(config.LAND_NAME_KEYWORDS)
    firms["land_in_name"] = firms["firm_key"].map(lambda k: bool(keywords & set(k.split())))
    firms = firms.drop_duplicates(subset="Lic_Number")
    logger.info("%d active licensed firms (%d with land wording in the name)",
                len(firms), int(firms["land_in_name"].sum()))
    return firms
