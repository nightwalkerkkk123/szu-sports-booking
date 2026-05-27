"""Extract cookies from browser context."""
import logging
from typing import Optional

logger = logging.getLogger("booking.api")


def extract_cookies_from_page(page) -> dict:
    """
    Extract cookies from a Playwright page object.

    Args:
        page: Playwright page object (from CloakBrowser.page)

    Returns:
        Dict of cookie name -> value
    """
    cookies = {}
    try:
        # Get all cookies from the page context
        page_cookies = page.context.cookies()
        for cookie in page_cookies:
            cookies[cookie["name"]] = cookie["value"]
        logger.info(f"Extracted {len(cookies)} cookies from page")
    except Exception as e:
        logger.error(f"Failed to extract cookies from page: {e}")
    return cookies


def extract_cookies_from_browser(browser_lifecycle) -> dict:
    """
    Extract cookies from a BrowserLifecycle implementation.

    Args:
        browser_lifecycle: CloakBrowserLifecycle or similar

    Returns:
        Dict of cookie name -> value
    """
    if not browser_lifecycle.is_launched():
        logger.warning("Browser not launched, no cookies to extract")
        return {}

    try:
        page = browser_lifecycle.page
        if page is None:
            logger.warning("No page available")
            return {}

        return extract_cookies_from_page(page)
    except Exception as e:
        logger.error(f"Failed to extract cookies: {e}")
        return {}


def extract_cookies_from_context(context) -> dict:
    """
    Extract cookies from a Playwright browser context.

    Args:
        context: Playwright browser context

    Returns:
        Dict of cookie name -> value
    """
    cookies = {}
    try:
        page_cookies = context.cookies()
        for cookie in page_cookies:
            cookies[cookie["name"]] = cookie["value"]
        logger.info(f"Extracted {len(cookies)} cookies from context")
    except Exception as e:
        logger.error(f"Failed to extract cookies from context: {e}")
    return cookies