import uuid
import json
import asyncio
from typing import AsyncGenerator, Dict, List
from datetime import datetime
from backend.agentic.fluid_engine import FluidEngine
from backend.analytics.segment_embedder import SegmentEmbedder
from backend.services.embedding_service import EmbeddingService
from backend.services.slm_client import SLMClient

class ChatSession:
    def __init__(self, session_id: str, title: str):
        self.session_id = session_id
        self.title = title
        self.created_at = datetime.utcnow().isoformat()
        self.message_count = 0

class ChatService:
    """Backend for the streaming chat sidebar and MCP tool dispatcher utilizing GPT4All natively."""
    def __init__(self, db_conn, embedder: EmbeddingService, segment_embedder: SegmentEmbedder, fluid_engine: FluidEngine):
        self.db = db_conn
        self.embedder = embedder
        self.segment_embedder = segment_embedder
        self.fluid_engine = fluid_engine
        self.slm_client = SLMClient()
        self.tool_registry = self._register_tools()
        
    def create_session(self, title: str = "New Chat") -> ChatSession:
        sid = str(uuid.uuid4())
        session = ChatSession(sid, title)
        query = "CREATE (s:ChatSession {session_id: $sid, title: $t, created_at: $c, message_count: 0})"
        try:
            self.db.execute(query, parameters={"sid": sid, "t": title, "c": session.created_at})
        except Exception as e:
            print(f"Error creating ChatSession: {e}")
        return session

    def _register_tools(self) -> Dict:
        return {
            'search_knowledge': self._tool_search_knowledge,
            'search_domains': self._tool_search_domains,
            'start_fluid': self._tool_start_fluid,
        }

    async def _tool_search_knowledge(self, params: Dict) -> Dict:
        query = params.get("query", "")
        res = self.segment_embedder.hybrid_search(query)
        return {"results": res}

    async def _tool_search_domains(self, params: Dict) -> Dict:
        return {"results": [{"url": "https://example.com", "title": "Example Domain", "snippet": "Simulation of domain scanning tool."}]}

    async def _tool_start_fluid(self, params: Dict) -> AsyncGenerator[Dict, None]:
        query = params.get("query", "Start fluid")
        return self.fluid_engine.propagate_fluid(query)

    async def send_message(self, session_id: str, content: str, node_context: Dict = None) -> AsyncGenerator[Dict, None]:
        """Real SLM response routing integrating MCP decision tree and text generation."""
        if node_context:
            yield {"type": "token", "content": f"*[Context: {node_context.get('xpath', 'unknown')}]*\n"}
            await asyncio.sleep(0.1)

        sys_prompt_router = (
            "You are a router. Evaluate the user's prompt to determine if you need to use an external tool.\n"
            "Tools available:\n"
            "- 'search_knowledge' (to find indexed graph facts or items)\n"
            "- 'start_fluid' (to trigger an autonomous multi-phase agentic research task)\n"
            "- 'none' (just answer directly)\n"
            "You must reply strictly using this JSON format: {\"tool\": \"tool_name\", \"query\": \"action text\"}"
        )

        decision = self.slm_client.generate_json(content, sys_prompt_router)
        tool_name = decision.get("tool", "none")
        tool_query = decision.get("query", content)

        if tool_name == "start_fluid":
            yield {"type": "tool_call", "tool_name": "start_fluid", "tool_input": {"query": tool_query}}
            async for fluid_event in self.fluid_engine.propagate_fluid(tool_query):
                yield {"type": "tool_result", "tool_name": "start_fluid", "tool_output": fluid_event}
                
        elif tool_name == "search_knowledge":
            yield {"type": "tool_call", "tool_name": "search_knowledge", "tool_input": {"query": tool_query}}
            res = await self._tool_search_knowledge({"query": tool_query})
            yield {"type": "tool_result", "tool_name": "search_knowledge", "tool_output": res}

        # Format Final Chat context based on execution
        sys_prompt_chat = "You are a helpful AI assistant within Web Fiber Haptics."
        chat_prompt = content
        if tool_name != "none":
            chat_prompt = f"User: {content}\nA Tool was executed. Acknowledge the user's workflow success."

        async for token in self.slm_client.async_stream_chat(chat_prompt, sys_prompt_chat):
            yield {"type": "token", "content": token}
            
        yield {"type": "done"}
