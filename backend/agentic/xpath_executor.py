class XPathExecutor:
    """Translates Agentic reasoning intents directly into low-level Document Object Model JavaScript scripts."""
    
    @staticmethod
    def _evaluate_prefix(xpath: str) -> str:
        """Helper to compute node extraction robustly using the evaluator protocol."""
        return f"""
        var result = document.evaluate('{xpath}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        var targetNode = result.singleNodeValue;
        """
        
    @staticmethod
    def compile_input_script(xpath: str, value: str) -> str:
        """Produces JS mimicking a keystroke string entry bounded to the targeted element."""
        # Note: Escaping mechanisms might be required for production values
        safe_value = value.replace('"', '\\"')
        
        script = XPathExecutor._evaluate_prefix(xpath)
        script += f"""
        if (targetNode) {{
            targetNode.value = "{safe_value}";
            targetNode.dispatchEvent(new Event("input", {{ bubbles: true }}));
            targetNode.dispatchEvent(new Event("change", {{ bubbles: true }}));
            return true;
        }}
        return false;
        """
        return script

    @staticmethod
    def compile_click_script(xpath: str) -> str:
        """Produces JS invoking a physical click."""
        script = XPathExecutor._evaluate_prefix(xpath)
        script += """
        if (targetNode) {
            targetNode.click();
            return true;
        }
        return false;
        """
        return script
