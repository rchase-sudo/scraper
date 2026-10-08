import logging
import os
import random
import re
import time
from functools import wraps

import config


def setup_logger(name: str) -> logging.Logger:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # avoid duplicate handlers on re-import
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = logging.FileHandler(os.path.join(config.LOG_DIR, f"{name}.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def random_user_agent() -> str:
    return random.choice(config.USER_AGENTS)


def random_viewport() -> dict:
    return random.choice(config.VIEWPORTS)


def random_proxy() -> str | None:
    if not config.PROXIES:
        return None
    return random.choice(config.PROXIES)


def polite_delay():
    """Randomized delay between requests so traffic doesn't look robotic."""
    time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))


def retry_with_backoff(max_retries: int = None, base_seconds: float = None):
    """Retries a function on exception with exponential backoff + jitter.
    A single blocked/failed listing should never kill the whole run — the
    caller is expected to also wrap call sites in try/except so that even
    after retries are exhausted, the run continues to the next item.
    """
    max_retries = max_retries or config.MAX_RETRIES
    base_seconds = base_seconds or config.BACKOFF_BASE_SECONDS

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 - intentionally broad, this is a scraper
                    last_exc = e
                    if attempt == max_retries:
                        break
                    sleep_for = base_seconds * (2 ** (attempt - 1)) + random.uniform(0, 3)
                    logging.getLogger(fn.__module__).warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt, max_retries, fn.__name__, e, sleep_for,
                    )
                    time.sleep(sleep_for)
            raise last_exc

        return wrapper

    return decorator


_NUMERIC_RE = re.compile(r"[\d.]+")


def parse_price(text: str) -> float | None:
    if not text:
        return None
    text = text.replace(",", "")
    # Only a K/M suffix directly after the number counts. Checking the whole
    # string for "k"/"m" turned "$250,000 - make an offer" into $250 trillion.
    match = re.search(r"(\d+(?:\.\d+)?)\s*(k|mm|m|thousand|million)?\b", text, re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    suffix = (match.group(2) or "").lower()
    if suffix in ("k", "thousand"):
        value *= 1_000
    elif suffix in ("m", "mm", "million"):
        value *= 1_000_000
    return value


def parse_acreage(text: str) -> float | None:
    if not text:
        return None
    text = text.replace(",", "")
    lower = text.lower()
    match = re.search(r"[\d.]+", text)
    if not match:
        return None
    try:
        value = float(match.group())
    except ValueError:
        return None
    if "sq ft" in lower or "sqft" in lower or "square feet" in lower:
        value = value / 43_560  # convert sq ft to acres
    return value


def normalize_phone(text: str) -> str:
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return text.strip()


def normalize_email(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return match.group().lower() if match else ""
