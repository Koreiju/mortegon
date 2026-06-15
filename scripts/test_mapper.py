import time, logging, asyncio, uuid
logging.basicConfig(level=logging.INFO)

from backend.dom.scanner import serialize_to_html
from backend.dom.shadow_html_parser import ShadowDOM
from backend.mapper.mapper import DomMapper
from backend.mapper.chunk_render import render_all_chunks

class MockStore:
    def __init__(self, *args, **kwargs): pass
    def save_snapshot(self, *args, **kwargs): pass
    def save_content_tree(self, *args, **kwargs): pass
    def get_snapshots_for_url(self, *args, **kwargs): return []
    def save_chunks(self, *args, **kwargs): pass
    def load_content_tree(self, *args, **kwargs): return None

class MockMapper(DomMapper):
    def __init__(self):
        super().__init__(driver=1)
        self.store = MockStore()
        self.intercepted_instances = []
        
    def _persist_instance_rows_only(self, *args, **kwargs):
        return len(kwargs.get('instances', []))

    def _build_chunks_for_streaming(self, *args, **kwargs):
        chunks, instances = super()._build_chunks_for_streaming(*args, **kwargs)
        self.intercepted_instances.extend(instances)
        print('INTERCEPTED CHUNKS:', len(chunks), 'INSTANCES:', len(instances))
        return chunks, instances

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
    def __init__(self):
        self._master_tree = master_tree
    def scan(self, *args, **kwargs):
        yield master_tree, []

import backend.mapper.mapper
backend.mapper.mapper.ShadowDOMScanner = lambda *args, **kwargs: MockScanner()

mapper = MockMapper()
mapper.snapshot('http://test.com')

print('TOTAL INSTANCES INTERCEPTED:', len(mapper.intercepted_instances))
if mapper.intercepted_instances:
    print('First text:', mapper.intercepted_instances[0].rendered_text)
