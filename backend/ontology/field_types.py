import enum
from typing import Optional

class TagEnum(enum.Enum):
    """Rigid semantic boundaries for parsed HTML tagging."""
    DIV = "div"
    SPAN = "span"
    A = "a"
    IMG = "img"
    INPUT = "input"
    BUTTON = "button"
    UL = "ul"
    LI = "li"
    NAV = "nav"
    # Extensible base definitions...

class TypeHandlerRegistry:
    """Type conversion layer enforcing typed validations over raw webpage extractions."""
    
    @staticmethod
    def handle_tag(raw_tag: str) -> Optional[TagEnum]:
        """Validates incoming strings against defined vocabulary constraints."""
        try:
            return TagEnum(raw_tag.lower())
        except ValueError:
            return None
            
    @staticmethod
    def handle_media_url(raw_attr: str) -> Optional[str]:
        """Resolves raw URLs and executes variant max-fidelity checks against `srcset`."""
        if not raw_attr:
            return None
            
        # Parse srcset 'small.png 200w, large.png 800w' behaviors
        if "w," in raw_attr or "w " in raw_attr:
            variants = [v.strip() for v in raw_attr.split(',')]
            best_url = None
            max_width = -1
            
            for variant in variants:
                parts = variant.strip().split(' ')
                if len(parts) >= 2:
                    url = parts[0]
                    # Parse trailing width dimensions natively
                    width_val = parts[-1].replace('w', '').replace('x', '')
                    try:
                        width = int(width_val)
                        if width > max_width:
                            max_width = width
                            best_url = url
                    except ValueError:
                        pass
            
            return best_url if best_url else variants[-1].split(' ')[0]
            
        return raw_attr
