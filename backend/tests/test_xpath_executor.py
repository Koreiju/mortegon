import pytest
from backend.agentic.xpath_executor import XPathExecutor

def test_xpath_js_script_compilation():
    """Verify that Agentic intents format natively into secure string-interpolated JavaScripts."""
    xpath = "/html/body/div[2]/input"
    fill_value = "Search Terms"
    
    script = XPathExecutor.compile_input_script(xpath, fill_value)
    
    # Assert critical selector and value boundaries are respected
    assert "document.evaluate" in script
    assert xpath in script
    assert fill_value in script
    
def test_xpath_click_script():
    """Verify JS click event generation."""
    xpath = "/html/body/button"
    script = XPathExecutor.compile_click_script(xpath)
    assert ".click()" in script
    assert xpath in script
