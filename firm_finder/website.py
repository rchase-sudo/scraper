"""Checks each firm's own public website for (1) wording that shows they do land
deals and (2) staff emails on team / about / contact pages.

Polite by design: honours robots.txt, identifies itself, waits between
requests, and only reads a handful of standard pages per site.
"""

import random
import re
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

import config
from common import clean_email, email_domain, setup_logger
from firms import Contact, Firm

logger = setup_logger("website")

_LAND_RES = [re.compile(p, re.I) for p in config.LAND_PATTERNS]
_NAME_RE = re.compile(r"^[A-Z][a-zA-Z.'\-]+(?: [A-Z][a-zA-Z.'\-]+){1,3}$")


class _PageParser(HTMLParser):
    """Collects visible text and mailto links (with their link text)."""

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.mailtos: list[tuple[str, str]] = []   # (email, link text)
        self._skip = 0
        self._mailto: str | None = None
        self._mailto_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.lower().startswith("mailto:"):
                self._mailto = href[7:].split("?")[0]
                self._mailto_text = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag == "a" and self._mailto is not None:
            self.mailtos.append((self._mailto, " ".join(self._mailto_text).strip()))
            self._mailto = None

    def handle_data(self, data):
        if self._skip:
            return
        self.text_parts.append(data)
        if self._mailto is not None:
            self._mailto_text.append(data.strip())

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text_parts))


def parse_page(html: str) -> tuple[str, list[tuple[str, str]]]:
    parser = _PageParser()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed HTML shouldn't stop the run
        pass
    return parser.text, parser.mailtos


def land_hits(text: str) -> list[str]:
    """Distinct land phrases found on a page, each with a little context."""
    hits = []
    for pattern in _LAND_RES:
        match = pattern.search(text)
        if match:
            start, end = max(0, match.start() - 40), min(len(text), match.end() + 40)
            hits.append(text[start:end].strip())
    return hits


def emails_from_page(text: str, mailtos: list[tuple[str, str]], firm_domain: str) -> list[Contact]:
    """Staff emails on the page. Keeps addresses on the firm's own domain and
    personal mailboxes (agents often use gmail); drops vendor/web-designer
    addresses on other domains."""
    found: dict[str, Contact] = {}
    candidates = [(email, label) for email, label in mailtos]
    candidates += [(m.group(), "") for m in re.finditer(r"[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}", text)]
    for raw, label in candidates:
        email = clean_email(raw)
        if not email:
            continue
        domain = email_domain(email)
        if domain != firm_domain and domain not in config.FREEMAIL_DOMAINS:
            continue
        name = label if _NAME_RE.match(label or "") else ""
        if email not in found or (name and not found[email].name):
            found[email] = Contact(name=name, email=email, role="website")
    return list(found.values())


class _Site:
    def __init__(self, domain: str, session: requests.Session):
        self.domain = domain
        self.session = session
        self.base = ""
        self.robots = RobotFileParser()

    def open(self) -> bool:
        """Finds a working base URL and loads robots.txt. False if the site is
        unreachable."""
        # robots.txt is the first (and only pre-check) request made to a site.
        for base in (f"https://{self.domain}", f"https://www.{self.domain}", f"http://{self.domain}"):
            try:
                resp = self.session.get(base + "/robots.txt", timeout=config.WEBSITE_TIMEOUT,
                                        allow_redirects=True)
            except requests.RequestException:
                continue
            if resp.status_code >= 500:
                continue
            final = urlparse(resp.url)
            self.base = f"{final.scheme}://{final.netloc}"
            is_text = "text/plain" in resp.headers.get("content-type", "text/plain")
            lines = resp.text.splitlines() if resp.status_code == 200 and is_text else []
            self.robots.parse(lines)   # missing robots.txt -> everything allowed
            return True
        return False

    def allowed(self, url: str) -> bool:
        return self.robots.can_fetch(config.USER_AGENT, url)

    def get(self, path: str) -> str | None:
        url = urljoin(self.base + "/", path.lstrip("/"))
        if not self.allowed(url):
            logger.info("robots.txt disallows %s, skipping", url)
            return None
        try:
            resp = self.session.get(url, timeout=config.WEBSITE_TIMEOUT)
        except requests.RequestException:
            return None
        if resp.status_code >= 400 or "html" not in resp.headers.get("content-type", "html"):
            return None
        return resp.text


def check_firm_website(firm: Firm, session: requests.Session | None = None) -> None:
    """Updates the firm in place with website, land wording hits and staff emails."""
    if not firm.domain:
        firm.website_status = "no website known"
        return
    session = session or _new_session()
    site = _Site(firm.domain, session)
    if not site.open():
        firm.website_status = "unreachable"
        return
    firm.website = site.base

    pages_read = 0
    for path in config.WEBSITE_PATHS[: config.MAX_PAGES_PER_SITE]:
        html = site.get(path)
        if html:
            pages_read += 1
            text, mailtos = parse_page(html)
            for hit in land_hits(text):
                if hit not in firm.website_land_hits:
                    firm.website_land_hits.append(hit)
            for contact in emails_from_page(text, mailtos, firm.domain):
                contact.source = urljoin(site.base + "/", path.lstrip("/"))
                firm.add_contact(contact)
        time.sleep(random.uniform(*config.WEBSITE_DELAY))

    firm.website_status = f"read {pages_read} page(s)" if pages_read else "no readable pages"
    logger.info("%s (%s): %d land mentions, %d contacts total",
                firm.name, site.base, len(firm.website_land_hits), len(firm.contacts))


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    return session


def check_websites(firms: list[Firm]) -> None:
    session = _new_session()
    with_domain = [f for f in firms if f.domain]
    logger.info("Checking websites for %d of %d firms (the rest have no known website).",
                len(with_domain), len(firms))
    for i, firm in enumerate(firms, 1):
        try:
            check_firm_website(firm, session)
        except Exception as e:  # noqa: BLE001 - one bad site must not stop the run
            firm.website_status = f"error: {e}"
            logger.error("Website check failed for %s: %s", firm.name, e)
        if firm.domain:
            logger.info("[%d/%d] %s -> %s", i, len(firms), firm.name, firm.website_status)
