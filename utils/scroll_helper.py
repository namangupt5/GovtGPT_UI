"""
Scroll Helper Module
Handles scroll behavior validation for Playwright automation.
"""

import logging
from collections.abc import Callable

from playwright.sync_api import Locator as SyncLocator, Page as SyncPage

logger = logging.getLogger(__name__)


class ScrollHelper:
    """
    Helper class for scroll behavior validation in the chatbot UI.
    Supports both sync and async Playwright operations.
    """

    def __init__(self, page: SyncPage):
        """
        Initialize scroll helper.

        Args:
            page: Playwright page object
        """
        self.page = page
        self._scroll_container_selector: str | None = None

    def set_scroll_container(self, selector: str) -> None:
        """Set the main scroll container selector."""
        self._scroll_container_selector = selector

    def get_scroll_position(self, container_selector: str | None = None) -> tuple[int, int]:
        """
        Get current scroll position of a container.

        Args:
            container_selector: CSS selector for scroll container

        Returns:
            Tuple of (scrollTop, scrollHeight)
        """
        selector = container_selector or self._scroll_container_selector

        if selector:
            position = self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        return {{
                            scrollTop: container.scrollTop,
                            scrollHeight: container.scrollHeight,
                            clientHeight: container.clientHeight
                        }};
                    }}
                    return {{ scrollTop: 0, scrollHeight: 0, clientHeight: 0 }};
                }}
            """)
        else:
            position = self.page.evaluate("""
                () => ({
                    scrollTop: window.scrollY || document.documentElement.scrollTop,
                    scrollHeight: document.documentElement.scrollHeight,
                    clientHeight: window.innerHeight
                })
            """)

        return position["scrollTop"], position["scrollHeight"]

    def is_scrolled_to_bottom(self, container_selector: str | None = None, threshold: int = 50) -> bool:
        """
        Check if container is scrolled to bottom.

        Args:
            container_selector: CSS selector for scroll container
            threshold: Pixel threshold for "at bottom" detection

        Returns:
            True if scrolled to bottom within threshold
        """
        selector = container_selector or self._scroll_container_selector

        if selector:
            result = self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= {threshold};
                        return isAtBottom;
                    }}
                    return false;
                }}
            """)
        else:
            result = self.page.evaluate(f"""
                () => {{
                    const isAtBottom = document.documentElement.scrollHeight - window.scrollY - window.innerHeight <= {threshold};
                    return isAtBottom;
                }}
            """)

        return result

    def scroll_to_bottom(self, container_selector: str | None = None, smooth: bool = True) -> None:
        """
        Scroll container to bottom.

        Args:
            container_selector: CSS selector for scroll container
            smooth: Use smooth scrolling animation
        """
        selector = container_selector or self._scroll_container_selector
        behavior = "smooth" if smooth else "instant"

        if selector:
            self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        container.scrollTo({{
                            top: container.scrollHeight,
                            behavior: '{behavior}'
                        }});
                    }}
                }}
            """)
        else:
            self.page.evaluate(f"""
                () => {{
                    window.scrollTo({{
                        top: document.documentElement.scrollHeight,
                        behavior: '{behavior}'
                    }});
                }}
            """)

        if smooth:
            self.page.wait_for_timeout(500)  # Wait for smooth scroll animation

    def scroll_to_top(self, container_selector: str | None = None, smooth: bool = True) -> None:
        """
        Scroll container to top.

        Args:
            container_selector: CSS selector for scroll container
            smooth: Use smooth scrolling animation
        """
        selector = container_selector or self._scroll_container_selector
        behavior = "smooth" if smooth else "instant"

        if selector:
            self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        container.scrollTo({{
                            top: 0,
                            behavior: '{behavior}'
                        }});
                    }}
                }}
            """)
        else:
            self.page.evaluate(f"""
                () => {{
                    window.scrollTo({{
                        top: 0,
                        behavior: '{behavior}'
                    }});
                }}
            """)

        if smooth:
            self.page.wait_for_timeout(500)

    def scroll_to_element(self, element: SyncLocator, smooth: bool = True) -> None:
        """
        Scroll to bring element into view.

        Args:
            element: Playwright locator for target element
            smooth: Use smooth scrolling animation
        """
        behavior = "smooth" if smooth else "instant"
        element.scroll_into_view_if_needed()

        if smooth:
            self.page.wait_for_timeout(300)

    def scroll_by(self, delta_y: int, container_selector: str | None = None) -> None:
        """
        Scroll by a specific amount.

        Args:
            delta_y: Pixels to scroll (positive = down, negative = up)
            container_selector: CSS selector for scroll container
        """
        selector = container_selector or self._scroll_container_selector

        if selector:
            self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        container.scrollBy(0, {delta_y});
                    }}
                }}
            """)
        else:
            self.page.evaluate(f"window.scrollBy(0, {delta_y})")

    def validate_auto_scroll_on_new_message(
        self, container_selector: str | None = None, message_action: Callable | None = None, timeout: int = 10000
    ) -> bool:
        """
        Validate that chat auto-scrolls when new message appears.

        Args:
            container_selector: CSS selector for scroll container
            message_action: Callable that triggers new message
            timeout: Timeout in milliseconds

        Returns:
            True if auto-scroll behavior is correct
        """
        selector = container_selector or self._scroll_container_selector

        # Get initial scroll position
        initial_top, initial_height = self.get_scroll_position(selector)
        logger.info(f"Initial scroll position: top={initial_top}, height={initial_height}")

        # Trigger new message if action provided
        if message_action:
            message_action()
            self.page.wait_for_timeout(1000)  # Wait for message to render

        # Get new scroll position
        new_top, new_height = self.get_scroll_position(selector)
        logger.info(f"New scroll position: top={new_top}, height={new_height}")

        # Validate scroll happened and is at bottom
        is_at_bottom = self.is_scrolled_to_bottom(selector)
        scroll_increased = new_height >= initial_height

        logger.info(f"Auto-scroll validation: at_bottom={is_at_bottom}, scroll_increased={scroll_increased}")

        return is_at_bottom and scroll_increased

    def get_scroll_metrics(self, container_selector: str | None = None) -> dict:
        """
        Get comprehensive scroll metrics.

        Args:
            container_selector: CSS selector for scroll container

        Returns:
            Dictionary with scroll metrics
        """
        selector = container_selector or self._scroll_container_selector

        if selector:
            metrics = self.page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{selector}');
                    if (container) {{
                        return {{
                            scrollTop: container.scrollTop,
                            scrollLeft: container.scrollLeft,
                            scrollHeight: container.scrollHeight,
                            scrollWidth: container.scrollWidth,
                            clientHeight: container.clientHeight,
                            clientWidth: container.clientWidth,
                            isScrollable: container.scrollHeight > container.clientHeight,
                            scrollPercentage: (container.scrollTop / (container.scrollHeight - container.clientHeight)) * 100
                        }};
                    }}
                    return null;
                }}
            """)
        else:
            metrics = self.page.evaluate("""
                () => ({
                    scrollTop: window.scrollY,
                    scrollLeft: window.scrollX,
                    scrollHeight: document.documentElement.scrollHeight,
                    scrollWidth: document.documentElement.scrollWidth,
                    clientHeight: window.innerHeight,
                    clientWidth: window.innerWidth,
                    isScrollable: document.documentElement.scrollHeight > window.innerHeight,
                    scrollPercentage: (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100
                })
            """)

        return metrics or {}

    def wait_for_scroll_idle(self, timeout: int = 2000, check_interval: int = 100) -> bool:
        """
        Wait until scrolling has stopped.

        Args:
            timeout: Maximum wait time in milliseconds
            check_interval: Interval between checks in milliseconds

        Returns:
            True if scroll became idle within timeout
        """
        elapsed = 0
        last_position = self.get_scroll_position()[0]
        stable_count = 0

        while elapsed < timeout:
            self.page.wait_for_timeout(check_interval)
            current_position = self.get_scroll_position()[0]

            if current_position == last_position:
                stable_count += 1
                if stable_count >= 3:  # Consider idle after 3 stable checks
                    return True
            else:
                stable_count = 0

            last_position = current_position
            elapsed += check_interval

        return False
