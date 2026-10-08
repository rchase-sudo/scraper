"""Small parsing helpers shared by the firm finder."""

import logging
import os
import re

import config

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
_JUNK_LOCALPARTS = ("noreply", "no-reply", "donotreply", "example", "test", "user", "email",
                    "yourname", "name", "wordpress", "webmaster")
_CORP_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|corp|corporation|co|company|ltd|lp|llp|pc|dba)\b\.?", re.I)


def setup_logger(name: str) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for handler in (logging.FileHandler(os.path.join("logs", f"{name}.log"), encoding="utf-8"),
                    logging.StreamHandler()):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def clean_email(value) -> str:
    """Returns a lowercase email, or "" if the value isn't a usable address."""
    if not value or not isinstance(value, str):
        return ""
    match = EMAIL_RE.search(value)
    if not match:
        return ""
    email = match.group().lower().strip(".")
    local, _, domain = email.partition("@")
    if email.endswith(_IMAGE_SUFFIXES) or "@2x" in email:
        return ""
    if local in _JUNK_LOCALPARTS or domain in config.PLATFORM_DOMAINS and local in ("info", "support"):
        return ""
    if domain in ("example.com", "sentry.io", "domain.com", "email.com"):
        return ""
    return email


def email_domain(email: str) -> str:
    return email.partition("@")[2].lower() if email else ""


def firm_domain_from_email(email: str) -> str:
    """The firm's own website domain, inferred from a staff email. "" for
    gmail-style personal mailboxes and big platform/franchise domains."""
    domain = email_domain(email)
    if not domain or domain in config.FREEMAIL_DOMAINS or domain in config.PLATFORM_DOMAINS:
        return ""
    return domain


def clean_phone(value) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def phones_from_field(value) -> list[str]:
    """HomeHarvest returns phones as a list of dicts ({"number": ..., "type": ...}),
    a list of strings, or a single string depending on the record."""
    if value is None:
        return []
    if isinstance(value, float):  # pandas NaN
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    phones = []
    for item in items:
        raw = item.get("number") if isinstance(item, dict) else item
        phone = clean_phone(raw)
        if phone and phone not in phones:
            phones.append(phone)
    return phones


def normalize_firm_name(name: str) -> str:
    """Key for matching the same firm across sources: lowercase, no
    punctuation, no Inc/LLC/Corp suffixes."""
    if not name or not isinstance(name, str):
        return ""
    name = _CORP_SUFFIXES.sub(" ", name.lower())
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def text_value(value) -> str:
    if value is None or isinstance(value, float):
        return ""
    return str(value).strip()
