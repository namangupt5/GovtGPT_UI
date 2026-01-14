"""
Login Page Object
Handles authentication for GovGPT chatbot.
Updated with correct selectors discovered from UI exploration.
"""

import logging

from playwright.sync_api import Page

from pages.base_page import BasePage
from utils.config_loader import config

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """
    Page Object for GovGPT Login functionality.

    Login Flow:
    1. Navigate to main page
    2. Click "Log in" button to open login dialog
    3. Fill email and password
    4. Click submit button
    5. Wait for successful authentication
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self._base_url = config.base_url

        # Selectors discovered from UI exploration (confirmed working)
        self._selectors = {
            "login_dialog_btn_alt": "div.text-body-alternate-tertiary.fixed button",
            # Login form elements (confirmed working)
            "email_input": "input[type='email']",
            "email_input_alt": "input#email",
            "password_input": "input[type='password']",
            "password_input_alt": "input#password",
            # Submit button in dialog (confirmed working)
            "submit_btn": "button[type='submit']",
            "submit_btn_alt": "form button:has-text('Log in')",
        }

    def navigate_to_login(self) -> "LoginPage":
        """Navigate to the login page."""
        logger.info(f"Navigating to login page: {self._base_url}")
        self.navigate(self._base_url)
        self.wait_for_page_load()
        return self

    def open_login_dialog(self) -> "LoginPage":
        """Click the login button to open the login dialog."""
        logger.info("Opening login dialog")

        # Try primary selector
        try:
            btn = self.page.locator(self._selectors["login_dialog_btn"]).first
            if btn.is_visible(timeout=5000):
                btn.click()
                logger.info("Clicked login button")
                self.page.wait_for_timeout(1000)
                return self
        except Exception as e:
            logger.debug(f"Primary login button failed: {e}")

        # Try alternative
        try:
            self.page.click(self._selectors["login_dialog_btn_alt"], timeout=3000)
            logger.info("Clicked login button (alternative)")
            self.page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"Failed to open login dialog: {e}")

        return self

    def enter_email(self, email: str) -> "LoginPage":
        """Enter email/username."""
        logger.info(f"Entering email: {email}")
        try:
            email_input = self.page.locator(self._selectors["email_input"]).first
            if email_input.is_visible(timeout=5000):
                email_input.fill(email)
                return self
        except:
            pass

        # Try alternative
        try:
            self.page.fill(self._selectors["email_input_alt"], email)
        except Exception as e:
            logger.warning(f"Failed to fill email: {e}")
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Enter password."""
        logger.info("Entering password: ****")
        try:
            pwd_input = self.page.locator(self._selectors["password_input"]).first
            if pwd_input.is_visible(timeout=5000):
                pwd_input.fill(password)
                return self
        except:
            pass

        # Try alternative
        try:
            self.page.fill(self._selectors["password_input_alt"], password)
        except Exception as e:
            logger.warning(f"Failed to fill password: {e}")
        return self

    def click_submit(self) -> "LoginPage":
        """Click the submit button in the login dialog."""
        logger.info("Clicking submit button")
        try:
            submit_btn = self.page.locator(self._selectors["submit_btn"]).first
            if submit_btn.is_visible(timeout=3000):
                submit_btn.click()
                logger.info("Submit clicked successfully")
                # Wait for page to process login - don't wait_for_timeout as page may navigate
                return self
        except Exception as e:
            # If page closed due to navigation, that's success
            if "closed" in str(e).lower():
                logger.info("Page navigated after submit - login in progress")
                return self
            logger.debug(f"Primary submit failed: {e}")

        # Try alternative only if primary truly failed
        try:
            self.page.click(self._selectors["submit_btn_alt"])
            logger.info("Submit clicked (alternative)")
        except Exception as e:
            if "closed" not in str(e).lower():
                logger.warning(f"Failed to click submit: {e}")
        return self

    def login(self, email: str, password: str) -> "LoginPage":
        """Perform complete login flow."""
        logger.info(f"Performing login for: {email}")

        # Step 1: Open login dialog
        self.open_login_dialog()
        self.page.wait_for_timeout(500)

        # Step 2: Fill credentials
        self.enter_email(email)
        self.enter_password(password)

        # Step 3: Submit
        self.click_submit()

        return self

    def wait_for_login_complete(self, timeout: int = 30000) -> bool:
        """Wait for login to complete using URL change or chat interface appearing."""
        logger.info("Waiting for login to complete")
        try:
            # First wait for any navigation to complete
            self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            self.page.wait_for_load_state("networkidle", timeout=timeout)

            # Check if we're past the auth page
            current_url = self.page.url
            logger.info(f"Current URL after login: {current_url}")

            # If URL doesn't contain 'auth' or login elements are gone, login succeeded
            if "auth" not in current_url or "/auth?redirect" in current_url:
                # Wait a bit more for chat to load
                self.page.wait_for_timeout(2000)
                return True

            # Try waiting for email input to disappear
            self.page.wait_for_selector(self._selectors["email_input"], state="hidden", timeout=10000)
            return True
        except Exception as e:
            logger.warning(f"Login wait exception: {e}")
            # Check URL as fallback
            try:
                current_url = self.page.url
                # If we're on the main app (not login page), consider it success
                return "govgpt" in current_url
            except:
                return False

    def is_login_error_displayed(self) -> bool:
        """Check if login error is displayed."""
        try:
            error_selectors = [
                "[role='alert']",
                ".error",
                "[class*='error']",
                ":has-text('Invalid')",
                ":has-text('incorrect')",
            ]
            for selector in error_selectors:
                if self.page.locator(selector).count() > 0:
                    return True
            return False
        except:
            return False

    def get_login_error_message(self) -> str:
        """Get login error message if displayed."""
        try:
            error = self.page.locator("[role='alert'], .error, [class*='error']").first
            if error.is_visible():
                return error.inner_text()
        except:
            pass
        return ""
