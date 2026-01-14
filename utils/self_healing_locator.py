"""
Self-Healing Locator Module
Implements dynamic locator discovery and self-healing capabilities.
Prefers role/text-based selectors and recovers from DOM changes automatically.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


@dataclass
class LocatorStrategy:
    """Represents a locator strategy with priority."""

    name: str
    selector: str
    priority: int
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


@dataclass
class HealingReport:
    """Report of healing attempts for a locator."""

    original_selector: str
    healed_selector: str | None = None
    strategies_tried: list[str] = field(default_factory=list)
    success: bool = False
    element_found: bool = False


class SelfHealingLocator:
    """
    Self-healing locator that dynamically discovers and heals broken locators.
    Implements vibe-coding behavior by adapting to UI changes.
    """

    def __init__(self, page: Page):
        self.page = page
        self._strategy_cache: dict[str, LocatorStrategy] = {}
        self._healing_history: list[HealingReport] = []

        # Priority order for locator strategies
        self._strategy_priorities = ["role", "text", "placeholder", "label", "testid", "css", "xpath"]

    def find_element(
        self, element_description: str, fallback_selectors: list[str] | None = None, timeout: int = 10000
    ) -> Locator | None:
        """
        Find element using self-healing strategies.

        Args:
            element_description: Human-readable description of element
            fallback_selectors: List of fallback selectors to try
            timeout: Timeout in milliseconds

        Returns:
            Locator if found, None otherwise
        """
        healing_report = HealingReport(original_selector=element_description)

        # Try cached strategy first
        if element_description in self._strategy_cache:
            cached = self._strategy_cache[element_description]
            locator = self._try_selector(cached.selector, timeout=timeout)
            if locator:
                cached.success_count += 1
                healing_report.success = True
                healing_report.element_found = True
                return locator
            cached.failure_count += 1

        # Try dynamic discovery strategies
        locator = self._discover_element(element_description, healing_report, timeout)
        if locator:
            self._healing_history.append(healing_report)
            return locator

        # Try fallback selectors
        if fallback_selectors:
            for selector in fallback_selectors:
                healing_report.strategies_tried.append(f"fallback:{selector}")
                locator = self._try_selector(selector, timeout=timeout)
                if locator:
                    self._cache_strategy(element_description, selector, "fallback")
                    healing_report.healed_selector = selector
                    healing_report.success = True
                    healing_report.element_found = True
                    self._healing_history.append(healing_report)
                    return locator

        self._healing_history.append(healing_report)
        logger.warning(f"Could not find element: {element_description}")
        return None

    def _discover_element(self, description: str, report: HealingReport, timeout: int) -> Locator | None:
        """Discover element using multiple strategies."""

        # Strategy 1: Role-based (ARIA)
        report.strategies_tried.append("role")
        locator = self._try_role_based(description, timeout)
        if locator:
            report.healed_selector = f"role:{description}"
            report.success = True
            report.element_found = True
            return locator

        # Strategy 2: Text-based
        report.strategies_tried.append("text")
        locator = self._try_text_based(description, timeout)
        if locator:
            report.healed_selector = f"text:{description}"
            report.success = True
            report.element_found = True
            return locator

        # Strategy 3: Placeholder-based
        report.strategies_tried.append("placeholder")
        locator = self._try_placeholder_based(description, timeout)
        if locator:
            report.healed_selector = f"placeholder:{description}"
            report.success = True
            report.element_found = True
            return locator

        # Strategy 4: Label-based
        report.strategies_tried.append("label")
        locator = self._try_label_based(description, timeout)
        if locator:
            report.healed_selector = f"label:{description}"
            report.success = True
            report.element_found = True
            return locator

        return None

    def _try_role_based(self, description: str, timeout: int) -> Locator | None:
        """Try to find element by ARIA role."""
        role_mappings = {
            "input": ["textbox", "searchbox", "combobox"],
            "button": ["button"],
            "send": ["button"],
            "submit": ["button"],
            "message": ["textbox", "searchbox"],
            "chat": ["textbox", "searchbox", "combobox"],
            "login": ["button"],
            "email": ["textbox"],
            "password": ["textbox"],
            "username": ["textbox"],
        }

        desc_lower = description.lower()

        # Find matching roles
        roles_to_try = []
        for keyword, roles in role_mappings.items():
            if keyword in desc_lower:
                roles_to_try.extend(roles)

        if not roles_to_try:
            roles_to_try = ["textbox", "button", "searchbox"]

        # Try each role
        for role in set(roles_to_try):
            try:
                # Try role with name
                locator = self.page.get_by_role(role, name=re.compile(description, re.IGNORECASE))
                if locator.count() > 0:
                    locator.first.wait_for(state="visible", timeout=timeout)
                    self._cache_strategy(description, f"role={role}", "role")
                    return locator.first
            except (PlaywrightTimeout, Exception):
                pass

            try:
                # Try role without name
                locator = self.page.get_by_role(role)
                if locator.count() > 0:
                    self._cache_strategy(description, f"role={role}", "role")
                    return locator.first
            except (PlaywrightTimeout, Exception):
                pass

        return None

    def _try_text_based(self, description: str, timeout: int) -> Locator | None:
        """Try to find element by text content."""
        try:
            locator = self.page.get_by_text(description, exact=False)
            if locator.count() > 0:
                locator.first.wait_for(state="visible", timeout=timeout)
                self._cache_strategy(description, f"text={description}", "text")
                return locator.first
        except (PlaywrightTimeout, Exception):
            pass

        # Try partial match
        try:
            words = description.split()
            for word in words:
                if len(word) > 3:
                    locator = self.page.get_by_text(word, exact=False)
                    if locator.count() > 0:
                        self._cache_strategy(description, f"text={word}", "text")
                        return locator.first
        except (PlaywrightTimeout, Exception):
            pass

        return None

    def _try_placeholder_based(self, description: str, timeout: int) -> Locator | None:
        """Try to find element by placeholder text."""
        try:
            locator = self.page.get_by_placeholder(re.compile(description, re.IGNORECASE))
            if locator.count() > 0:
                locator.first.wait_for(state="visible", timeout=timeout)
                self._cache_strategy(description, f"placeholder={description}", "placeholder")
                return locator.first
        except (PlaywrightTimeout, Exception):
            pass

        # Try common placeholder patterns
        placeholders = ["type", "enter", "message", "ask", "search", "query", "email", "password", "username"]

        desc_lower = description.lower()
        for placeholder in placeholders:
            if placeholder in desc_lower:
                try:
                    locator = self.page.get_by_placeholder(re.compile(placeholder, re.IGNORECASE))
                    if locator.count() > 0:
                        self._cache_strategy(description, f"placeholder={placeholder}", "placeholder")
                        return locator.first
                except (PlaywrightTimeout, Exception):
                    pass

        return None

    def _try_label_based(self, description: str, timeout: int) -> Locator | None:
        """Try to find element by label."""
        try:
            locator = self.page.get_by_label(re.compile(description, re.IGNORECASE))
            if locator.count() > 0:
                locator.first.wait_for(state="visible", timeout=timeout)
                self._cache_strategy(description, f"label={description}", "label")
                return locator.first
        except (PlaywrightTimeout, Exception):
            pass

        return None

    def _try_selector(self, selector: str, timeout: int = 5000) -> Locator | None:
        """Try a specific selector."""
        try:
            locator = self.page.locator(selector)
            if locator.count() > 0:
                locator.first.wait_for(state="visible", timeout=timeout)
                return locator.first
        except (PlaywrightTimeout, Exception):
            pass
        return None

    def _cache_strategy(self, description: str, selector: str, strategy_name: str) -> None:
        """Cache a successful strategy."""
        priority = self._strategy_priorities.index(strategy_name) if strategy_name in self._strategy_priorities else 99
        self._strategy_cache[description] = LocatorStrategy(
            name=strategy_name, selector=selector, priority=priority, success_count=1
        )
        logger.debug(f"Cached strategy for '{description}': {strategy_name} -> {selector}")

    def find_chat_input(self, timeout: int = 10000) -> Locator | None:
        """Find chat input field using self-healing."""
        fallbacks = [
            "div#chat-input",
            "textarea",
            "input[type='text']",
            "[contenteditable='true']",
            ".chat-input",
            "#chat-input",
            "[data-testid='chat-input']",
            "[placeholder*='message' i]",
            "[placeholder*='type' i]",
            "[placeholder*='ask' i]",
        ]
        return self.find_element("chat input message", fallbacks, timeout)

    def find_send_button(self, timeout: int = 10000) -> Locator | None:
        """Find send button using self-healing."""
        fallbacks = [
            "button[type='submit']",
            "[aria-label*='send' i]",
            "[data-testid='send-button']",
            ".send-button",
            "#send-button",
            "button:has-text('Send')",
            "button:has-text('Submit')",
            "button svg",  # Icon button
        ]
        return self.find_element("send button", fallbacks, timeout)

    def find_login_email_input(self, timeout: int = 10000) -> Locator | None:
        """Find email/username input for login."""
        fallbacks = [
            "input[type='email']",
            "input[name='email']",
            "input[name='username']",
            "input[id*='email' i]",
            "input[id*='user' i]",
            "[placeholder*='email' i]",
            "[placeholder*='username' i]",
        ]
        return self.find_element("email username input", fallbacks, timeout)

    def find_login_password_input(self, timeout: int = 10000) -> Locator | None:
        """Find password input for login."""
        fallbacks = [
            "input[type='password']",
            "input[name='password']",
            "input[id*='password' i]",
            "[placeholder*='password' i]",
        ]
        return self.find_element("password input", fallbacks, timeout)

    def find_login_button(self, timeout: int = 10000) -> Locator | None:
        """Find login/submit button."""
        fallbacks = [
            "div.text-body-alternate-tertiary.fixed button",  # GovGPT specific
            "button[type='submit']",
            "[data-testid='login-button']",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button:has-text('Submit')",
            "input[type='submit']",
        ]
        return self.find_element("login submit button", fallbacks, timeout)

    def find_chat_messages(self, timeout: int = 10000) -> Locator | None:
        """Find chat message container."""
        fallbacks = [
            "[data-testid='chat-messages']",
            ".chat-messages",
            ".messages-container",
            ".conversation",
            "[role='log']",
            "[aria-label*='conversation' i]",
        ]
        return self.find_element("chat messages container", fallbacks, timeout)

    def find_last_response(self, timeout: int = 10000) -> Locator | None:
        """Find the last AI response message."""
        fallbacks = [
            "[data-testid='assistant-message']:last-child",
            ".assistant-message:last-child",
            ".ai-response:last-child",
            ".bot-message:last-child",
            "[data-role='assistant']:last-child",
        ]
        return self.find_element("last AI response", fallbacks, timeout)

    def find_loading_indicator(self, timeout: int = 5000) -> Locator | None:
        """Find loading/spinner indicator."""
        fallbacks = [
            "[data-testid='loading']",
            ".loading",
            ".spinner",
            "[aria-busy='true']",
            "[role='progressbar']",
            ".typing-indicator",
        ]
        return self.find_element("loading indicator", fallbacks, timeout)

    def get_healing_report(self) -> list[dict[str, Any]]:
        """Get healing history report."""
        return [
            {
                "original": r.original_selector,
                "healed": r.healed_selector,
                "strategies_tried": r.strategies_tried,
                "success": r.success,
                "element_found": r.element_found,
            }
            for r in self._healing_history
        ]

    def clear_cache(self) -> None:
        """Clear strategy cache."""
        self._strategy_cache.clear()
        logger.info("Locator strategy cache cleared")
