from dataclasses import dataclass
from typing import Dict, List, Callable

@dataclass
class AgentTool:
    name: str
    description: str
    handler: Callable
    requires_browser: bool = False

class ToolRegistry:
    """Registry of tools available to agentic fluid particles."""

    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self._register_defaults()

    def register(self, tool: AgentTool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get_tool_inventory(self, tool_names: List[str] = None) -> str:
        """Format tool descriptions as a prompt block."""
        inventory = []
        for name, tool in self.tools.items():
            if tool_names is None or name in tool_names:
                inventory.append(f"- {name}: {tool.description}")
        return "\n".join(inventory)

    def chunk_inventory(self, max_tokens: int = 2048) -> List[str]:
        """Chunk the tool inventory into prompt blocks under ``max_tokens``
        (whitespace-word proxy, same estimate ContextManager uses). One
        tool's line is never split across chunks; a single line longer
        than the budget becomes its own chunk. (Previously a stub that
        returned the whole inventory unconditionally — an empty mock in a
        production path, §R.8.)"""
        budget = max(1, int(max_tokens))
        lines = [ln for ln in self.get_tool_inventory().split("\n") if ln]
        chunks: List[str] = []
        cur: List[str] = []
        cur_tokens = 0
        for ln in lines:
            ln_tokens = len(ln.split())
            if cur and cur_tokens + ln_tokens > budget:
                chunks.append("\n".join(cur))
                cur, cur_tokens = [], 0
            cur.append(ln)
            cur_tokens += ln_tokens
        if cur:
            chunks.append("\n".join(cur))
        return chunks

    def _register_defaults(self):
        self.register(AgentTool("web_search", "Search web via DuckDuckGo", self._web_search))
        self.register(AgentTool("database_search", "Query KuzuDB", self._database_search))
        self.register(AgentTool("dom_retrieval", "Load DOM data", self._dom_retrieval))
        self.register(AgentTool("read_note", "Read saved user note by UUID", self._read_note))
        self.register(AgentTool("write_note", "Write a new user note", self._write_note))

    # Built-in tools:
    def _web_search(self, query: str) -> str: return "Search results mocked"
    def _database_search(self, cypher_query: str) -> str: return "DB results mocked"
    def _dom_retrieval(self, url: str, xpath: str) -> str: return "DOM results mocked"
    def _read_note(self, note_id: str) -> str: return "Note mocked"
    def _write_note(self, title: str, content: str) -> str: return "Saved"
