"""
Base Page Module
Provides common functionality for all page objects.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page, expect

from utils.config_loader import config
from utils.scroll_helper import ScrollHelper

logger = logging.getLogger(__name__)


class BasePage:
    """
    Base page class providing common functionality for all page objects.
    Implements core Playwright interactions with built-in logging and reporting.
    """

    def __init__(self, page: Page):
        """
        Initialize base page.

        Args:
            page: Playwright page object
        """
        self.page = page
        self.scroll_helper = ScrollHelper(page)
        self._timeout = config.get("browser.timeout", 30000)
        self._screenshot_dir = Path(config.get("reporting.screenshots.dir", "reports/screenshots"))
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    @property
    def url(self) -> str:
        """Get current page URL."""
        return self.page.url

    @property
    def title(self) -> str:
        """Get current page title."""
        return self.page.title()

    def navigate(self, url: str) -> None:
        """
        Navigate to URL.

        Args:
            url: URL to navigate to
        """
        logger.info(f"Navigating to: {url}")
        self.page.goto(url, wait_until="domcontentloaded")

    def wait_for_page_load(self, timeout: int | None = None) -> None:
        """Wait for page to fully load."""
        self.page.wait_for_load_state("networkidle", timeout=timeout or self._timeout)

    def find_element(self, selector: str) -> Locator:
        """
        Find element by selector.

        Args:
            selector: CSS or XPath selector

        Returns:
            Playwright Locator
        """
        return self.page.locator(selector)

    def find_elements(self, selector: str) -> Locator:
        """
        Find all elements matching selector.

        Args:
            selector: CSS or XPath selector

        Returns:
            Playwright Locator for all matches
        """
        return self.page.locator(selector)

    def click(self, selector: str, timeout: int | None = None) -> None:
        """
        Click element.

        Args:
            selector: Element selector
            timeout: Optional timeout override
        """
        logger.debug(f"Clicking: {selector}")
        self.page.click(selector, timeout=timeout or self._timeout)

    def fill(self, selector: str, text: str, clear_first: bool = True) -> None:
        """
        Fill input field.

        Args:
            selector: Input selector
            text: Text to enter
            clear_first: Clear field before filling
        """
        logger.debug(f"Filling '{selector}' with text (length: {len(text)})")
        if clear_first:
            self.page.fill(selector, "")
        self.page.fill(selector, text)

    def type_text(self, selector: str, text: str, delay: int = 50) -> None:
        """
        Type text character by character.

        Args:
            selector: Input selector
            text: Text to type
            delay: Delay between keystrokes in ms
        """
        logger.debug(f"Typing into: {selector}")
        self.page.locator(selector).press_sequentially(text, delay=delay)

    def get_text(self, selector: str) -> str:
        """
        Get element text content.

        Args:
            selector: Element selector

        Returns:
            Text content
        """
        return self.page.locator(selector).inner_text()

    def get_attribute(self, selector: str, attribute: str) -> str | None:
        """
        Get element attribute value.

        Args:
            selector: Element selector
            attribute: Attribute name

        Returns:
            Attribute value or None
        """
        return self.page.locator(selector).get_attribute(attribute)

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """
        Check if element is visible.

        Args:
            selector: Element selector
            timeout: Wait timeout

        Returns:
            True if visible
        """
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def is_hidden(self, selector: str, timeout: int = 5000) -> bool:
        """
        Check if element is hidden.

        Args:
            selector: Element selector
            timeout: Wait timeout

        Returns:
            True if hidden
        """
        try:
            self.page.locator(selector).wait_for(state="hidden", timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for_element(self, selector: str, state: str = "visible", timeout: int | None = None) -> Locator:
        """
        Wait for element to reach specified state.

        Args:
            selector: Element selector
            state: Target state ('visible', 'hidden', 'attached', 'detached')
            timeout: Optional timeout override

        Returns:
            Locator for the element
        """
        locator = self.page.locator(selector)
        locator.wait_for(state=state, timeout=timeout or self._timeout)
        return locator

    def wait_for_text(self, selector: str, text: str, timeout: int | None = None) -> None:
        """
        Wait for element to contain text.

        Args:
            selector: Element selector
            text: Expected text
            timeout: Optional timeout override
        """
        expect(self.page.locator(selector)).to_contain_text(text, timeout=timeout or self._timeout)

    def take_screenshot(self, name: str = None, full_page: bool = True) -> str:
        """
        Take screenshot and attach to Allure report.

        Args:
            name: Screenshot name
            full_page: Capture full page

        Returns:
            Screenshot file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name or 'screenshot'}_{timestamp}.png"
        filepath = self._screenshot_dir / filename

        screenshot_bytes = self.page.screenshot(full_page=full_page)

        with open(filepath, "wb") as f:
            f.write(screenshot_bytes)

        logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)

    def attach_to_allure(self, content: str, name: str, attachment_type: str = "text") -> None:
        """
        Attach content to Allure report.
        NOTE: This method is deprecated to avoid duplicate attachments.
        Allure-behave handles attachments automatically.
        """
        # Disabled to prevent duplicate attachments in Allure report
        pass

    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in page context.

        Args:
            script: JavaScript code
            *args: Arguments to pass to script

        Returns:
            Script return value
        """
        return self.page.evaluate(script, *args)

    def wait_for_network_idle(self, timeout: int | None = None) -> None:
        """Wait for network to become idle."""
        self.page.wait_for_load_state("networkidle", timeout=timeout or self._timeout)

    def press_key(self, key: str) -> None:
        """
        Press keyboard key.

        Args:
            key: Key to press (e.g., 'Enter', 'Tab', 'Escape')
        """
        self.page.keyboard.press(key)

    def get_all_text_contents(self, selector: str) -> list[str]:
        """
        Get text content of all matching elements.

        Args:
            selector: Element selector

        Returns:
            List of text contents
        """
        return self.page.locator(selector).all_inner_texts()

    def count_elements(self, selector: str) -> int:
        """
        Count elements matching selector.

        Args:
            selector: Element selector

        Returns:
            Number of matching elements
        """
        return self.page.locator(selector).count()

    def assert_element_visible(self, selector: str, message: str = None) -> None:
        """
        Assert element is visible.

        Args:
            selector: Element selector
            message: Custom assertion message
        """
        expect(self.page.locator(selector)).to_be_visible()

    def assert_element_hidden(self, selector: str, message: str = None) -> None:
        """
        Assert element is hidden.

        Args:
            selector: Element selector
            message: Custom assertion message
        """
        expect(self.page.locator(selector)).to_be_hidden()

    def assert_text_present(self, selector: str, text: str, message: str = None) -> None:
        """
        Assert element contains text.

        Args:
            selector: Element selector
            text: Expected text
            message: Custom assertion message
        """
        expect(self.page.locator(selector)).to_contain_text(text)
