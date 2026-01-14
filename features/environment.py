"""
Behave Environment Configuration
Sets up browser, pages, and test context for each scenario.
"""

import logging
from datetime import datetime
from pathlib import Path

import allure
from playwright.sync_api import sync_playwright

# =============================================================================
# Allure-Behave Fix for KeyError in stop_scenario/drop_test
# This patches the AllureReporter to handle missing UUIDs gracefully
# =============================================================================
try:
    from allure_commons.reporter import AllureReporter

    # Save original methods
    _original_drop_test = AllureReporter.drop_test
    _original_close_test = AllureReporter.close_test
    _original_get_test = AllureReporter.get_test

    def _safe_drop_test(self, uuid):
        """Safely drop a test, ignoring KeyError if UUID doesn't exist."""
        try:
            return _original_drop_test(self, uuid)
        except KeyError:
            logging.getLogger(__name__).debug(f"Allure: drop_test ignored for missing UUID: {uuid}")

    def _safe_close_test(self, uuid):
        """Safely close a test, ignoring KeyError if UUID doesn't exist."""
        try:
            return _original_close_test(self, uuid)
        except KeyError:
            logging.getLogger(__name__).debug(f"Allure: close_test ignored for missing UUID: {uuid}")

    def _safe_get_test(self, uuid):
        """Safely get a test, returning None if UUID doesn't exist."""
        try:
            return _original_get_test(self, uuid)
        except KeyError:
            logging.getLogger(__name__).debug(f"Allure: get_test returning None for missing UUID: {uuid}")
            return None

    # Apply patches
    AllureReporter.drop_test = _safe_drop_test
    AllureReporter.close_test = _safe_close_test
    AllureReporter.get_test = _safe_get_test

    logging.getLogger(__name__).debug("Allure-behave KeyError fix applied successfully")
except Exception as e:
    logging.getLogger(__name__).warning(f"Failed to apply allure-behave fix: {e}")


from pages.chat_page import ChatPage
from pages.login_page import LoginPage
from utils.audit_logger import AuditLogger
from utils.config_loader import config
from utils.excel_reader import ExcelReader
from validators.grammar_validator import GrammarValidator
from validators.relevance_validator import RelevanceValidator
from validators.safety_validator import SafetyValidator
from validators.semantic_validator import SemanticValidator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def before_all(context):
    """Setup before all tests."""
    logger.info("=" * 60)
    logger.info("Starting GovGPT Chatbot Test Automation")
    logger.info("=" * 60)

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "allure-results").mkdir(exist_ok=True)
    (reports_dir / "screenshots").mkdir(exist_ok=True)

    # Load Excel test data - use absolute path
    project_root = Path(__file__).parent.parent
    excel_path = project_root / "data" / "uae_gov_chatbot_prompts.xlsx"
    context.excel_reader = ExcelReader(str(excel_path))
    logger.info(f"Loaded {len(context.excel_reader.prompts)} prompts from Excel")

    # Initialize validators (lazy loading)
    context.safety_validator = SafetyValidator()
    context.relevance_validator = RelevanceValidator()
    context.grammar_validator = GrammarValidator()
    context.semantic_validator = SemanticValidator()

    # Initialize audit logger
    context.audit_logger = AuditLogger()

    # Store test results
    context.test_results = []


def before_scenario(context, scenario):
    """Setup before each scenario."""
    logger.info("-" * 60)
    logger.info(f"Starting scenario: {scenario.name}")
    logger.info("-" * 60)

    # Launch browser with stability options
    context.playwright = sync_playwright().start()

    browser_type = config.get("browser.type", "chromium")
    headless = config.is_headless
    slow_mo = config.get("browser.slow_mo", 100)

    logger.info(f"Launching {browser_type} (headless: {headless})")

    # Chrome/Chromium stability arguments
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--allow-running-insecure-content",
        "--start-maximized",
        "--window-size=1920,1080",
    ]

    # Add device-scale forcing for Chromium to avoid macOS retina scaling issues
    if browser_type == "chromium":
        browser_args += ["--force-device-scale-factor=1", "--high-dpi-support=1"]

    if browser_type == "chromium":
        context.browser = context.playwright.chromium.launch(headless=headless, slow_mo=slow_mo, args=browser_args)
    elif browser_type == "firefox":
        context.browser = context.playwright.firefox.launch(headless=headless, slow_mo=slow_mo)
    elif browser_type == "webkit":
        context.browser = context.playwright.webkit.launch(headless=headless, slow_mo=slow_mo)

    # For Chromium prefer using the actual browser window size (viewport=None) and set device_scale_factor
    if browser_type == "chromium":
        context.browser_context = context.browser.new_context(
            viewport=None,
            device_scale_factor=1,
            record_video_dir="reports/videos" if config.get("browser.video_recording") else None,
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
        )
    else:
        # default context with configured viewport
        viewport = config.get("browser.viewport", {"width": 1920, "height": 1080})
        context.browser_context = context.browser.new_context(
            viewport=viewport,
            record_video_dir="reports/videos" if config.get("browser.video_recording") else None,
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
        )

    # Create page
    context.page = context.browser_context.new_page()

    # Set default timeouts - longer for stability
    context.page.set_default_timeout(60000)
    context.page.set_default_navigation_timeout(90000)

    # Wait for browser to be fully ready
    context.page.wait_for_timeout(1000)

    # Initialize page objects
    context.login_page = LoginPage(context.page)
    context.chat_page = ChatPage(context.page)

    # Scenario data
    context.current_prompt = None
    context.current_response = None
    context.current_response_data = None
    context.current_prompt_id = None
    context.current_risk_level = None
    context.current_expected_intent = None
    context.scenario_start_time = datetime.now()

    # NOTE: Allure tags/title are handled automatically by allure-behave formatter
    # No need for allure.dynamic calls here


def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    logger.info(f"Scenario completed: {scenario.name} - {scenario.status}")

    # Take screenshot on failure and attach to Allure
    if scenario.status == "failed":
        try:
            screenshot_path = f"reports/screenshots/{scenario.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_FAILED.png"
            screenshot_bytes = context.page.screenshot(full_page=True)

            # Save to file
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)

            # Attach to Allure
            allure.attach(screenshot_bytes, name="❌ Failure Screenshot", attachment_type=allure.attachment_type.PNG)
            logger.info(f"Failure screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}")

    # NOTE: All attachments (prompts, responses, validations) are in step definitions
    # to show on the relevant steps in Allure report

    # Record test result for internal tracking
    result = {
        "scenario": scenario.name,
        "status": str(scenario.status),
        "prompt_id": context.current_prompt_id,
        "duration": (datetime.now() - context.scenario_start_time).total_seconds(),
    }
    context.test_results.append(result)

    # Close browser
    try:
        context.page.close()
        context.browser_context.close()
        context.browser.close()
        context.playwright.stop()
    except Exception as e:
        logger.warning(f"Error closing browser: {e}")


def after_all(context):
    """Cleanup after all tests."""
    logger.info("=" * 60)
    logger.info("Test Execution Complete")
    logger.info("=" * 60)

    # Generate summary report
    total = len(context.test_results)
    passed = sum(1 for r in context.test_results if r["status"] == "passed")
    failed = total - passed

    logger.info(f"Total Scenarios: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Pass Rate: {(passed / total) * 100:.1f}%" if total > 0 else "N/A")

    # Generate audit report
    if hasattr(context, "audit_logger"):
        context.audit_logger.generate_session_report()

    # Clean up duplicate allure result files (keep only the one with most steps)
    _cleanup_duplicate_allure_results()


def _cleanup_duplicate_allure_results():
    """
    Clean up allure result files:
    1. Remove duplicate result files (keep only one with most steps)
    2. Remove duplicate sub-steps from each step
    3. Remove duplicate attachments from steps and test level
    """
    import json
    import os

    allure_results_dir = Path("reports/allure-results")
    if not allure_results_dir.exists():
        return

    # Group result files by test name
    results_by_name = {}
    for result_file in allure_results_dir.glob("*-result.json"):
        try:
            with open(result_file) as f:
                data = json.load(f)
            test_name = data.get("name", "")
            steps_count = len(data.get("steps", []))

            if test_name not in results_by_name:
                results_by_name[test_name] = []
            results_by_name[test_name].append((result_file, steps_count, data))
        except Exception as e:
            logger.debug(f"Error reading allure result file {result_file}: {e}")

    def dedupe_attachments(attachments):
        """Remove duplicate attachments by name."""
        seen_names = set()
        unique = []
        for att in attachments:
            att_name = att.get("name", "")
            if att_name not in seen_names:
                seen_names.add(att_name)
                unique.append(att)
        return unique

    # Process each test
    for test_name, results in results_by_name.items():
        # Sort by steps count descending, keep the first one
        results.sort(key=lambda x: x[1], reverse=True)

        # Keep the best result and process it
        best_result_file, _, best_data = results[0]

        # Process steps
        if "steps" in best_data:
            for step in best_data["steps"]:
                substeps = step.get("steps", [])

                # Collect all attachments from step and substeps
                all_attachments = step.get("attachments", [])
                for ss in substeps:
                    all_attachments.extend(ss.get("attachments", []))

                # Dedupe and set attachments on parent step
                step["attachments"] = dedupe_attachments(all_attachments)

                # Remove duplicate sub-steps (same name as parent)
                step_name = step.get("name", "")
                if len(substeps) == 1 and substeps[0].get("name", "") == step_name:
                    step["steps"] = []

        # Remove duplicate attachments at test level
        if "attachments" in best_data:
            best_data["attachments"] = dedupe_attachments(best_data["attachments"])

        # Write cleaned data back
        try:
            with open(best_result_file, "w") as f:
                json.dump(best_data, f, indent=2)
        except Exception as e:
            logger.debug(f"Error writing cleaned result file: {e}")

        # Remove duplicate result files
        if len(results) > 1:
            for result_file, steps_count, _ in results[1:]:
                try:
                    os.remove(result_file)
                    logger.debug(f"Removed duplicate allure result: {result_file}")
                except Exception as e:
                    logger.debug(f"Failed to remove duplicate: {e}")
