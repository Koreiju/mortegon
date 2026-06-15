"""
js_utilities.py
Enhanced JavaScript utilities for Fibre Web Haptics.
"""

SHADOW_XPATH_ENHANCED_JS = """
function resolveXPathWithShadow(xpath, context) {
    // Initialize with context or document
    const root = context || document;
    const results = [];
    
    try {
        // First try standard XPath
        const xpathResult = root.evaluate(
            xpath,
            root,
            null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
            null
        );
        
        for (let i = 0; i < xpathResult.snapshotLength; i++) {
            results.push(xpathResult.snapshotItem(i));
        }
    } catch (e) {
        console.warn('Standard XPath failed:', e.message);
    }
    
    // If no results, try shadow DOM traversal
    if (results.length === 0) {
        const walker = (node) => {
            // Check if node matches XPath (simplified)
            if (node.nodeType === Node.ELEMENT_NODE) {
                // Try to match against tag and attributes
                const tag = node.tagName.toLowerCase();
                const id = node.id || '';
                const className = node.className || '';
                
                // Simple heuristic: check if xpath contains tag name
                if (xpath.includes(tag)) {
                    // Check if attributes match
                    let matches = true;
                    const attrMatches = xpath.match(/@([^=\[\]]+)=['"]([^'"]+)['"]/g) || [];
                    
                    for (const attrMatch of attrMatches) {
                        const [_, attrName, attrValue] = attrMatch.match(/@([^=]+)=['"]([^'"]+)['"]/);
                        const actualValue = node.getAttribute(attrName);
                        
                        if (!actualValue || !actualValue.includes(attrValue)) {
                            matches = false;
                            break;
                        }
                    }
                    
                    if (matches) {
                        results.push(node);
                    }
                }
            }
            
            // Check shadow root
            if (node.shadowRoot) {
                walker(node.shadowRoot);
            }
            
            // Check children
            for (const child of node.childNodes) {
                walker(child);
            }
        };
        
        walker(root);
    }
    
    return results;
}

// Convert CSS-style selectors to XPath when needed
function normalizeSelector(selector) {
    // If it starts with //, it's already XPath
    if (selector.startsWith('//') || selector.startsWith('.//') || selector.startsWith('/')) {
        return selector;
    }
    
    // Convert CSS to XPath (simple cases)
    if (selector.startsWith('#')) {
        return `//*[@id="${selector.slice(1)}"]`;
    } else if (selector.startsWith('.')) {
        return `//*[contains(@class, "${selector.slice(1)}")]`;
    }
    
    return selector;
}

// Main function
function main(selector) {
    const normalized = normalizeSelector(selector);
    console.log('Resolving selector:', normalized);
    
    const elements = resolveXPathWithShadow(normalized);
    console.log('Found elements:', elements.length);
    
    if (elements.length > 0) {
        // Return first element for interaction
        return [elements[0]];
    }
    
    // Fallback: try document.querySelector for simple selectors
    try {
        const simpleElements = document.querySelectorAll(selector);
        if (simpleElements.length > 0) {
            return Array.from(simpleElements);
        }
    } catch (e) {
        console.warn('Query selector failed:', e);
    }
    
    return [];
}

return main(arguments[0]);
"""

SHADOW_XPATH_JS = SHADOW_XPATH_ENHANCED_JS

# Additional interaction scripts
CLICK_JS = """
function clickElement(selector) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
        elements[0].click();
        return true;
    }
    return false;
}
return clickElement(arguments[0]);
"""

TYPE_JS = """
function typeIntoElement(selector, text) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
        const el = elements[0];
        el.focus();
        el.value = text;
        
        // Trigger events
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        
        return true;
    }
    return false;
}
return typeIntoElement(arguments[0], arguments[1]);
"""

SCROLL_JS = """
window.scrollBy(0, arguments[0]);
return document.documentElement.scrollTop;
"""

GET_ELEMENT_JS = """
function getElement(selector) {
    // Try XPath first
    try {
        const result = document.evaluate(
            selector,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        const node = result.singleNodeValue;
        if (node) return node;
    } catch (e) {}
    
    // Fallback to querySelector
    return document.querySelector(selector);
}
return getElement(arguments[0]);
"""