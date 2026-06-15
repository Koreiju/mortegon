import sys; sys.path.insert(0, 'c:/Users/isaac/Documents/web_fiber_haptics')
import time, logging, asyncio, uuid
logging.basicConfig(level=logging.INFO)

from backend.dom.scanner import serialize_to_html
from backend.dom.shadow_html_parser import ShadowDOM
from backend.mapper.mapper import DomMapper
from backend.mapper.chunk_render import render_all_chunks
from backend.database import get_connection

html = '<html><body><div><p>Hello world!</p><a href="#">Link</a></div></body></html>'

mapper = DomMapper(driver=1)

master_tree = {
    "nodeType": 1,
    "tagName": "html",
    "attributes": {},
    "children": [
        {
            "nodeType": 1,
            "tagName": "body",
            "attributes": {},
            "children": [
                {
                    "nodeType": 1,
                    "tagName": "div",
                    "attributes": {},
                    "children": [
                        {
                            "nodeType": 1,
                            "tagName": "p",
                            "attributes": {"data-content-hash": "123"},
                            "children": [
                                {
                                    "nodeType": 3,
                                    "textContent": "Hello world!"
                                }
                            ]
                        },
                        {
                            "nodeType": 1,
                            "tagName": "a",
                            "attributes": {"href": "#", "data-content-hash": "456"},
                            "children": [
                                {
                                    "nodeType": 3,
                                    "textContent": "Link"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

from backend.dom.scanner import compute_node_signature
def add_sigs(n):
    n['_node_sig'] = compute_node_signature(n)
    for c in n.get('children', []): add_sigs(c)
add_sigs(master_tree)

class MockScanner:
    def __init__(self, *args, **kwargs):
        self._master_tree = master_tree
    def scan(self, *args, **kwargs):
        yield master_tree, []

import backend.mapper.mapper
backend.mapper.mapper.ShadowDOMScanner = MockScanner

mapper.snapshot('http://test.com')

conn = get_connection()
res = conn.execute("MATCH (n:ChunkInstance) RETURN count(n)")
while res.has_next():
    print('ChunkInstance count:', res.get_next()[0])
