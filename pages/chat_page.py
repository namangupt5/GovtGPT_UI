"""
Chat Page Object
Handles chat interface interactions for GovGPT chatbot.
Updated with correct selectors discovered from UI exploration.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage
from utils.config_loader import config
from utils.self_healing_locator import SelfHealingLocator

logger = logging.getLogger(__name__)


@dataclass
class ResponseData:
    """Structured AI response data for validation."""

    full_text: str
    paragraphs: list[str] = field(default_factory=list)
    word_count: int = 0
    paragraph_count: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.paragraphs and self.full_text:
            self.paragraphs = [p.strip() for p in self.full_text.split("\n\n") if p.strip()]
        self.word_count = len(self.full_text.split()) if self.full_text else 0
        self.paragraph_count = len(self.paragraphs)
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "full_text": self.full_text,
            "paragraphs": self.paragraphs,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "timestamp": self.timestamp,
        }

    def get_first_paragraph(self) -> str:
        """Get first paragraph (often contains key response)."""
        return self.paragraphs[0] if self.paragraphs else ""

    def contains_refusal(self) -> bool:
        """Check if response contains refusal language."""
        refusal_keywords = [
            "sorry",
            "cannot",
            "can't",
            "unable",
            "not able",
            "apologize",
            "inappropriate",
            "not authorized",
        ]
        text_lower = self.full_text.lower()
        return any(kw in text_lower for kw in refusal_keywords)


class ChatPage(BasePage):
    """
    Page Object for GovGPT Chat Interface.

    Chat elements discovered:
    - Chat input: [contenteditable='true']
    - Send button: button with svg icon
    """

    def __init__(self, page: Page):
        super().__init__(page)
        self.healer = SelfHealingLocator(page)
        self._response_timeout = config.get("ui_behavior.loader.timeout", 60000)

        # Selectors discovered from UI exploration (confirmed working)
        self._selectors = {
            # Chat input - contenteditable div
            "chat_input": "[contenteditable='true']",
            "chat_input_alt": "textarea",
            # Send button - in submit-button-container (confirmed working)
            "send_btn": "div.submit-button-container button",
            "send_btn_alt": "button:has(svg)",
            # Response container - paragraphs inside response-content-container (confirmed working)
            "response_container": "div#response-content-container p",
            "response_container_alt": "[class*='message' i]",
            # Messages container
            "messages_container": "[class*='message' i]",
            "assistant_message": "[class*='assistant' i], [class*='bot' i], [class*='ai' i]",
            # Loading indicator
            "loading": "[class*='loading' i], [class*='typing' i], [class*='spinner' i]",
        }

    def is_chat_ready(self) -> bool:
        """Check if chat interface is ready using self-healing first."""
        try:
            chat_input = self.healer.find_chat_input(timeout=5000)
            return bool(chat_input)
        except Exception:
            return False

    def get_chat_input(self) -> Locator | None:
        """Get the chat input element via self-healing with known fallbacks."""
        locator = self.healer.find_chat_input(timeout=5000)
        if locator:
            return locator

        # Try alternative
        try:
            input_el = self.page.locator(self._selectors["chat_input_alt"]).first
            if input_el.is_visible():
                return input_el
        except:
            pass

        return None

    def type_message(self, message: str) -> "ChatPage":
        """Type a message in the chat input with realistic delay."""
        logger.info(f"Typing message (length: {len(message)} chars)")

        # Wait for UI to be ready before typing
        self.page.wait_for_timeout(1000)

        chat_input = self.get_chat_input()
        if chat_input:
            # Ensure input is ready and focused
            try:
                chat_input.wait_for(state="visible", timeout=5000)
                chat_input.click(timeout=5000)
                self.page.wait_for_timeout(300)  # Small wait after click
                chat_input.fill("")  # Clear any existing text
                self.page.wait_for_timeout(200)  # Wait after clear
                chat_input.type(message, delay=30)  # Type like a human
                logger.info("Message typed successfully")
            except Exception as e:
                logger.warning(f"Chat input interaction failed: {e}")
                # Fallback to keyboard
                self.page.keyboard.type(message, delay=30)
        else:
            logger.warning("Using keyboard fallback for chat input")
            self.page.keyboard.type(message, delay=30)
        return self

    def click_send(self) -> "ChatPage":
        """Click the send button using discovered selector."""
        logger.info("Clicking send button")

        # Try primary selector first
        try:
            send_btn = self.page.locator(self._selectors["send_btn"]).first
            if send_btn.is_visible(timeout=3000):
                send_btn.click()
                logger.info("Clicked send button")
                return self
        except Exception as e:
            logger.debug(f"Primary send selector failed: {e}")

        # Try alternative
        try:
            send_btn = self.page.locator(self._selectors["send_btn_alt"]).first
            if send_btn.is_visible(timeout=2000):
                send_btn.click()
                logger.info("Clicked send button (alt)")
                return self
        except Exception as e:
            logger.debug(f"Alt send selector failed: {e}")

        # Try Enter key as fallback
        try:
            logger.info("Trying Enter key to send")
            self.page.keyboard.press("Enter")
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")

        return self

    def send_message(self, message: str) -> "ChatPage":
        """Type and send a message."""
        logger.info(f"Sending message: {message[:50]}...")
        self.type_message(message)
        self.page.wait_for_timeout(500)  # Wait after typing before clicking send
        self.click_send()
        self.page.wait_for_timeout(500)  # Wait after send for UI to process
        return self

    def send_prompt_from_excel(self, prompt: str) -> "ChatPage":
        """Send a prompt from Excel - same as send_message but with logging."""
        logger.info(f"Sending Excel prompt: {prompt[:50]}...")
        return self.send_message(prompt)

    def wait_for_response(self, timeout: int = None) -> bool:
        """Wait for AI response by polling for loading indicator and new messages."""
        timeout_ms = timeout or self._response_timeout
        start = time.time()

        # Baseline message count
        try:
            base_count = len(self.get_all_messages())
        except Exception:
            base_count = 0

        while (time.time() - start) * 1000 < timeout_ms:
            # Check loading indicator presence then disappearance
            loading = self.healer.find_loading_indicator(timeout=500)
            if loading:
                try:
                    loading.wait_for(state="hidden", timeout=5000)
                except Exception:
                    pass

            current_messages = self.get_all_messages()
            if len(current_messages) > base_count:
                return True

            self.page.wait_for_timeout(400)

        logger.warning("Response wait timeout reached")
        return False

    def get_last_response(self) -> str | None:
        """Get the last AI response text from response container paragraphs."""
        logger.info("Capturing last response")

        # Try primary response container with paragraphs
        try:
            paragraphs = self.get_response_paragraphs()
            if paragraphs:
                response_text = "\n\n".join(paragraphs)
                logger.info(f"Found response ({len(response_text)} chars, {len(paragraphs)} paragraphs)")
                return response_text
        except Exception as e:
            logger.debug(f"Primary response capture failed: {e}")

        # Fallback to alternative selectors
        try:
            elements = self.page.locator(self._selectors["response_container_alt"]).all()
            if elements:
                last_el = elements[-1]
                if last_el.is_visible():
                    text = last_el.inner_text()
                    if text and len(text.strip()) > 10:
                        logger.info(f"Found response via fallback ({len(text)} chars)")
                        return text.strip()
        except Exception as e:
            logger.debug(f"Fallback response capture failed: {e}")

        # Last resort: get from main content area
        try:
            main_content = self.page.locator("main, [role='main'], .chat-container").first
            if main_content.is_visible():
                text = main_content.inner_text()
                blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 20]
                if blocks:
                    return blocks[-1]
        except:
            pass

        logger.warning("Could not capture response")
        return None

    def get_response_paragraphs(self) -> list[str]:
        """Get AI response as list of paragraphs for validation."""
        paragraphs = []
        try:
            p_elements = self.page.locator(self._selectors["response_container"]).all()
            for p_el in p_elements:
                if p_el.is_visible():
                    p_text = p_el.inner_text().strip()
                    if p_text:
                        paragraphs.append(p_text)
        except Exception as e:
            logger.warning(f"Failed to get response paragraphs: {e}")
        return paragraphs

    def get_all_messages(self) -> list[str]:
        """Get all messages in the chat (self-healing container first)."""
        messages = []
        container = self.healer.find_chat_messages(timeout=1000)
        if container:
            try:
                elements = container.all()
            except Exception:
                elements = []
        else:
            elements = []
        if not elements:
            try:
                elements = self.page.locator(self._selectors["messages_container"]).all()
            except Exception:
                elements = []
        for el in elements:
            try:
                text = el.inner_text()
                if text.strip():
                    messages.append(text.strip())
            except Exception:
                continue
        return messages

    def is_scrolled_to_bottom(self) -> bool:
        """Check if chat is scrolled to bottom."""
        try:
            result = self.page.evaluate("""
                () => {
                    const container = document.querySelector('[class*="chat"], [class*="message"], main');
                    if (container) {
                        return container.scrollTop + container.clientHeight >= container.scrollHeight - 50;
                    }
                    return true;
                }
            """)
            return result
        except:
            return True

    def is_input_cleared(self) -> bool:
        """Check if chat input is cleared after sending."""
        try:
            chat_input = self.get_chat_input()
            if chat_input:
                text = chat_input.inner_text()
                return len(text.strip()) == 0
            return True
        except:
            return True

    def take_screenshot(self, name: str = None, full_page: bool = True) -> str:
        """Take a screenshot with given name."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{name or 'screenshot'}_{timestamp}.png"
        path = f"reports/screenshots/{filename}"
        try:
            self.page.screenshot(path=path, full_page=full_page)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.warning(f"Failed to save screenshot: {e}")
        return path

    def get_response_data(self) -> ResponseData | None:
        """Get structured AI response data for validation."""
        logger.info("Capturing structured response data")

        paragraphs = self.get_response_paragraphs()
        if paragraphs:
            full_text = "\n\n".join(paragraphs)
            return ResponseData(full_text=full_text, paragraphs=paragraphs)

        # Fallback to get_last_response
        full_text = self.get_last_response()
        if full_text:
            return ResponseData(full_text=full_text)

        return None

    def wait_and_capture_response(self, timeout: int = None) -> ResponseData | None:
        """Wait for AI response and return structured data."""
        success = self.wait_for_response(timeout)
        if not success:
            logger.warning("Response wait timed out, attempting capture anyway")

        # Small additional wait for response to fully render
        self.page.wait_for_timeout(1000)

        return self.get_response_data()
