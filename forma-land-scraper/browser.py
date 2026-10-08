"""Shared Playwright browser/context setup with basic stealth + rate limiting."""

from contextlib import contextmanager

from playwright.sync_api import sync_playwright

import config
from utils import random_user_agent, random_viewport, random_proxy, setup_logger

logger = setup_logger("browser")

# Hides the most common headless/automation fingerprints (navigator.webdriver,
# missing chrome object, plugin/language arrays that look scripted, etc).
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
"""


@contextmanager
def new_page():
    """Yields a Playwright page configured with a randomized fingerprint.
    Caller is responsible for calling utils.polite_delay() between navigations
    and wrapping page interactions in try/except so one bad page doesn't
    kill the run.
    """
    proxy = random_proxy()
    launch_kwargs = {"headless": config.HEADLESS}
    if proxy:
        launch_kwargs["proxy"] = {"server": proxy}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=random_user_agent(),
            viewport=random_viewport(),
            locale="en-US",
            timezone_id="America/New_York",
        )
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()
