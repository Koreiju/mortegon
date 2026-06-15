"""Tests for the ActionExecutor service."""
import pytest
from backend.services.action_executor import ActionExecutor, BrowserAction, ActionResult


def test_no_browser_returns_error():
    executor = ActionExecutor(browser_manager=None)
    result = executor.execute("click", "/html/body/button")
    assert not result.success
    assert "No browser" in result.error


def test_unknown_action_returns_error():
    executor = ActionExecutor(browser_manager=None)
    result = executor.execute("explode", "/html/body")
    assert not result.success
    assert "No browser" in result.error


def test_browser_action_enum():
    assert BrowserAction.CLICK.value == "click"
    assert BrowserAction.FILL.value == "fill"
    assert BrowserAction.EXTRACT.value == "extract"
    assert BrowserAction.NAVIGATE.value == "navigate"
    assert BrowserAction.SCROLL_TO.value == "scroll_to"
    assert BrowserAction.SUBMIT.value == "submit"
    assert BrowserAction.SELECT.value == "select"
    assert BrowserAction.HOVER.value == "hover"


def test_action_result_dataclass():
    result = ActionResult(success=True, action="click", xpath="/html/body/button", value=None)
    assert result.success
    assert result.error is None


class MockDriver:
    def __init__(self):
        self.clicks = []
        self.fills = []

    def find_element(self, by, xpath):
        return MockElement(xpath, self)

    def execute_script(self, *args):
        return None

    def get(self, url):
        pass


class MockElement:
    def __init__(self, xpath, driver):
        self.xpath = xpath
        self._driver = driver
        self.text = "Mock text content"

    def click(self):
        self._driver.clicks.append(self.xpath)

    def clear(self):
        pass

    def send_keys(self, value):
        self._driver.fills.append((self.xpath, value))

    def submit(self):
        pass

    def get_attribute(self, attr):
        return f"mock-{attr}"


class MockBrowser:
    def __init__(self):
        self.driver = MockDriver()


def test_click_with_mock_browser():
    browser = MockBrowser()
    executor = ActionExecutor(browser_manager=browser)
    result = executor.execute("click", "/html/body/button")
    assert result.success
    assert "/html/body/button" in browser.driver.clicks


def test_fill_with_mock_browser():
    browser = MockBrowser()
    executor = ActionExecutor(browser_manager=browser)
    result = executor.execute("fill", "/html/body/input", value="hello world")
    assert result.success
    assert ("/html/body/input", "hello world") in browser.driver.fills


def test_extract_text_with_mock_browser():
    browser = MockBrowser()
    executor = ActionExecutor(browser_manager=browser)
    result = executor.execute("extract", "/html/body/p")
    assert result.success
    assert result.value == "Mock text content"


def test_extract_attribute_with_mock_browser():
    browser = MockBrowser()
    executor = ActionExecutor(browser_manager=browser)
    result = executor.execute("extract", "/html/body/a", options={"attribute": "href"})
    assert result.success
    assert result.value == "mock-href"


def test_navigate_with_mock_browser():
    browser = MockBrowser()
    executor = ActionExecutor(browser_manager=browser)
    result = executor.execute("navigate", "https://example.com", value="https://example.com")
    assert result.success
