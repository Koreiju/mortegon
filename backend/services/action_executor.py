"""
Phase 5 — XPath-targeted action executor (section 16).

Executes browser actions (click, fill, scroll, extract) targeted at
specific DOM nodes via their XPath. Powers both the GUI action buttons
and the agentic fluid tool invocations.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BrowserAction(str, Enum):
    """Browser action ontology (section 16)."""
    CLICK = "click"
    FILL = "fill"
    SCROLL_TO = "scroll_to"
    EXTRACT = "extract"
    NAVIGATE = "navigate"
    SUBMIT = "submit"
    SELECT = "select"
    HOVER = "hover"


@dataclass
class ActionResult:
    """Result of a browser action."""
    success: bool
    action: str
    xpath: str
    value: Any = None
    error: Optional[str] = None


class ActionExecutor:
    """
    Executes browser actions on specific DOM nodes via Selenium.

    Each action resolves the XPath to a concrete DOM element, executes
    the requested operation, and returns the result.
    """

    def __init__(self, browser_manager=None):
        self._browser = browser_manager

    def execute(
        self,
        action: str,
        xpath: str,
        value: Any = None,
        options: Dict = None,
    ) -> ActionResult:
        """
        Execute a browser action on the element at the given XPath.
        """
        if not self._browser:
            return ActionResult(
                success=False, action=action, xpath=xpath,
                error="No browser session available"
            )

        try:
            action_enum = BrowserAction(action)
        except ValueError:
            return ActionResult(
                success=False, action=action, xpath=xpath,
                error=f"Unknown action: {action}"
            )

        dispatch = {
            BrowserAction.CLICK: self._click,
            BrowserAction.FILL: self._fill,
            BrowserAction.SCROLL_TO: self._scroll_to,
            BrowserAction.EXTRACT: self._extract,
            BrowserAction.NAVIGATE: self._navigate,
            BrowserAction.SUBMIT: self._submit,
            BrowserAction.SELECT: self._select,
            BrowserAction.HOVER: self._hover,
        }

        handler = dispatch.get(action_enum)
        if handler is None:
            return ActionResult(
                success=False, action=action, xpath=xpath,
                error=f"No handler for action: {action}"
            )

        return handler(xpath, value, options or {})

    def _resolve_element(self, xpath: str):
        """Resolve an XPath to a Selenium WebElement."""
        driver = self._browser.driver if hasattr(self._browser, "driver") else None
        if driver is None:
            raise RuntimeError("No active Selenium driver")

        # Handle shadow-root XPaths by using JavaScript evaluation
        if "#shadow-root" in xpath:
            return self._resolve_shadow_xpath(driver, xpath)

        from selenium.webdriver.common.by import By
        return driver.find_element(By.XPATH, xpath)

    def _resolve_shadow_xpath(self, driver, xpath: str):
        """Resolve XPaths containing #shadow-root segments via JS."""
        js = f"""
        function resolveXPath(path) {{
            var parts = path.split('/#shadow-root/');
            var current = document.evaluate(
                parts[0], document, null,
                XPathResult.FIRST_ORDERED_NODE_TYPE, null
            ).singleNodeValue;
            if (!current) return null;
            for (var i = 1; i < parts.length; i++) {{
                current = current.shadowRoot;
                if (!current) return null;
                current = current.querySelector(parts[i].replace(/\\[\\d+\\]/g, ''));
            }}
            return current;
        }}
        return resolveXPath("{xpath}");
        """
        return driver.execute_script(js)

    def _click(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            element.click()
            return ActionResult(success=True, action="click", xpath=xpath)
        except Exception as e:
            return ActionResult(success=False, action="click", xpath=xpath, error=str(e))

    def _fill(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            clear_first = options.get("clear", True)
            if clear_first:
                element.clear()
            element.send_keys(str(value))
            return ActionResult(success=True, action="fill", xpath=xpath, value=value)
        except Exception as e:
            return ActionResult(success=False, action="fill", xpath=xpath, error=str(e))

    def _scroll_to(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            driver = self._browser.driver
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", element)
            return ActionResult(success=True, action="scroll_to", xpath=xpath)
        except Exception as e:
            return ActionResult(success=False, action="scroll_to", xpath=xpath, error=str(e))

    def _extract(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            attr = options.get("attribute")
            if attr:
                extracted = element.get_attribute(attr)
            else:
                extracted = element.text
            return ActionResult(success=True, action="extract", xpath=xpath, value=extracted)
        except Exception as e:
            return ActionResult(success=False, action="extract", xpath=xpath, error=str(e))

    def _navigate(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            url = value or xpath
            driver = self._browser.driver
            driver.get(url)
            return ActionResult(success=True, action="navigate", xpath=xpath, value=url)
        except Exception as e:
            return ActionResult(success=False, action="navigate", xpath=xpath, error=str(e))

    def _submit(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            element.submit()
            return ActionResult(success=True, action="submit", xpath=xpath)
        except Exception as e:
            return ActionResult(success=False, action="submit", xpath=xpath, error=str(e))

    def _select(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            from selenium.webdriver.support.select import Select
            select = Select(element)
            if isinstance(value, int):
                select.select_by_index(value)
            else:
                select.select_by_visible_text(str(value))
            return ActionResult(success=True, action="select", xpath=xpath, value=value)
        except Exception as e:
            return ActionResult(success=False, action="select", xpath=xpath, error=str(e))

    def _hover(self, xpath: str, value: Any, options: Dict) -> ActionResult:
        try:
            element = self._resolve_element(xpath)
            driver = self._browser.driver
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).move_to_element(element).perform()
            return ActionResult(success=True, action="hover", xpath=xpath)
        except Exception as e:
            return ActionResult(success=False, action="hover", xpath=xpath, error=str(e))
