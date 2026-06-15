from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
import json
from urllib.parse import urljoin

class TagEnum(str, Enum):
    """HTML vocabulary tags + structural pseudo-tags."""
    DIV = 'div'; SPAN = 'span'; A = 'a'; P = 'p'; H1 = 'h1'
    H2 = 'h2'; H3 = 'h3'; H4 = 'h4'; H5 = 'h5'; H6 = 'h6'
    UL = 'ul'; OL = 'ol'; LI = 'li'; NAV = 'nav'; MAIN = 'main'
    SECTION = 'section'; ARTICLE = 'article'; ASIDE = 'aside'
    HEADER = 'header'; FOOTER = 'footer'
    INPUT = 'input'; BUTTON = 'button'; FORM = 'form'; SELECT = 'select'
    TEXTAREA = 'textarea'; OPTION = 'option'; LABEL = 'label'
    IMG = 'img'; VIDEO = 'video'; AUDIO = 'audio'; SOURCE = 'source'
    PICTURE = 'picture'; FIGURE = 'figure'; FIGCAPTION = 'figcaption'
    TABLE = 'table'; TR = 'tr'; TD = 'td'; TH = 'th'; TBODY = 'tbody'
    IFRAME = 'iframe'; SVG = 'svg'; PATH = 'path'
    TEXT = '#text'; COMMENT = '#comment'; SHADOW_ROOT = '#shadow-root'
    UNKNOWN = 'unknown'
    
    @classmethod
    def safe_parse(cls, tag: str) -> 'TagEnum':
        try:
            return cls(tag.lower())
        except ValueError:
            return cls.UNKNOWN

class ContentCategory(str, Enum):
    URL_INTERNAL = 'url_internal'
    URL_EXTERNAL = 'url_external'
    MEDIA_IMAGE = 'media_image'
    MEDIA_VIDEO = 'media_video'
    MEDIA_AUDIO = 'media_audio'
    MEDIA_ARCHIVE = 'media_archive'
    TEXT_VISIBLE = 'text_visible'
    TEXT_ACCESSIBLE = 'text_accessible'
    TEXT_METADATA = 'text_metadata'
    INTERACTIVE = 'interactive'
    JSON_EMBEDDED = 'json_embedded'

class InteractiveType(str, Enum):
    SEARCH_INPUT = 'search_input'
    FORM_INPUT = 'form_input'
    PAGINATION_CONTROL = 'pagination_control'
    SORT_CONTROL = 'sort_control'
    FILTER_CONTROL = 'filter_control'
    NAVIGATION_LINK = 'navigation_link'
    ACTION_BUTTON = 'action_button'
    MEDIA_CONTROL = 'media_control'
    TOGGLE_SWITCH = 'toggle_switch'

class InputType(str, Enum):
    TEXT = 'text'; PASSWORD = 'password'; EMAIL = 'email'
    SEARCH = 'search'; URL = 'url'; TEL = 'tel'
    NUMBER = 'number'; DATE = 'date'; CHECKBOX = 'checkbox'
    RADIO = 'radio'; FILE = 'file'; HIDDEN = 'hidden'
    SUBMIT = 'submit'; BUTTON = 'button'; RANGE = 'range'
    COLOR = 'color'

@dataclass
class TypedDomNode:
    """Hard-typed DOM node with validated fields (§4B)."""
    xpath: str
    tag: TagEnum
    depth: int
    text_content: Optional[str] = None
    href: Optional[str] = None          
    src: Optional[str] = None           
    aria_label: Optional[str] = None
    role: Optional[str] = None          
    input_type: Optional[InputType] = None
    class_names: List[str] = field(default_factory=list)
    data_attrs: Dict[str, Any] = field(default_factory=dict)
    event_handlers: List[str] = field(default_factory=list)
    content_categories: Set[ContentCategory] = field(default_factory=set)
    media_assets: List[str] = field(default_factory=list)
    interactive_type: Optional[InteractiveType] = None
    numeric_attrs: Dict[str, float] = field(default_factory=dict)
    boolean_attrs: Dict[str, bool] = field(default_factory=dict)
    raw_attrs: Dict[str, str] = field(default_factory=dict)
    search_input_score: Optional[float] = None  
    pagination_score: Optional[float] = None     

class TypeHandlerRegistry:
    """Registry of type conversion handlers for DOM attributes (§4B.2).
    
    Each handler maps a raw string to a typed value, or None on failure.
    """

    def __init__(self, base_url: str = ''):
        self.base_url = base_url
        self._handlers: Dict[str, Callable] = {}
        self._register_defaults()

    def convert_node(self, raw_node: Dict[str, Any]) -> TypedDomNode:
        """
        Convert a raw DOM node dict to a fully typed TypedDomNode.
        Invalid values default to None and are preserved in `raw_attrs`.
        """
        raw_attrs = raw_node.get('attributes', {})
        if not isinstance(raw_attrs, dict):
            raw_attrs = {}
            
        tag_raw = raw_node.get('tagName', raw_node.get('nodeName', 'unknown'))
        typed_node = TypedDomNode(
            xpath=raw_node.get('xpath', '/'),
            tag=TagEnum.safe_parse(tag_raw),
            depth=raw_node.get('depth', 0),
            text_content=raw_node.get('textContent', '').strip() or None,
            raw_attrs=raw_attrs
        )

        for attr_key, raw_val in raw_attrs.items():
            key_lower = attr_key.lower()
            val_str = str(raw_val).strip()

            # Process standard attributes through handlers. The handler key
            # is the HTML attribute name; the destination is the dataclass
            # FIELD name — they differ for class/type/aria-label. (A bare
            # setattr(key_lower) silently wrote to nonexistent attributes,
            # leaving class_names/input_type/aria_label forever empty — the
            # InteractiveRanker reads exactly those three, so search-input
            # + pagination ranking was degraded. §4B typed-fields contract.)
            if key_lower in self._handlers:
                field_name = self._ATTR_TO_FIELD.get(key_lower, key_lower)
                setattr(typed_node, field_name, self._handlers[key_lower](val_str))
            
            # Process data-* attributes
            elif key_lower.startswith('data-'):
                if val_str.startswith('{') or val_str.startswith('['):
                    try:
                        typed_node.data_attrs[key_lower] = json.loads(val_str)
                    except json.JSONDecodeError:
                        typed_node.data_attrs[key_lower] = val_str
                else:
                    typed_node.data_attrs[key_lower] = val_str
                    
            # Process event handlers
            elif key_lower.startswith('on'):
                typed_node.event_handlers.append(key_lower)

        return typed_node

    #: HTML attribute name → TypedDomNode field name (identity when absent).
    _ATTR_TO_FIELD = {
        'class': 'class_names',
        'type': 'input_type',
        'aria-label': 'aria_label',
    }

    def _register_defaults(self):
        """Register default handlers for standard HTML attributes."""
        self._handlers['class'] = lambda v: sorted(list(set(v.split()))) if v else []
        self._handlers['href'] = lambda v: urljoin(self.base_url, v) if v else None
        self._handlers['src'] = lambda v: urljoin(self.base_url, v) if v else None
        self._handlers['aria-label'] = lambda v: v if v else None
        self._handlers['role'] = lambda v: v.lower() if v else None
        
        def parse_input_type(v: str) -> Optional[InputType]:
            try: return InputType(v.lower())
            except ValueError: return None
        self._handlers['type'] = parse_input_type