import asyncio
from typing import List, Dict, Callable, AsyncGenerator
from dataclasses import dataclass
from backend.services.slm_client import SLMClient

@dataclass
class AgentSpec:
    name: str
    domain: str
    description: str
    system_prompt: str
    tools: List[str]

@dataclass
class AgentTool:
    name: str
    description: str
    handler: Callable
    requires_browser: bool = False

class ContextManager:
    """Aggregate and chunk user-tailored context."""
    def gather_context(self, urls: List[str] = None) -> str:
        return "Aggregated Knowledge Graph Context."
        
    def chunk_context(self, context: str, max_tokens: int = 4096) -> List[str]:
        return [context]

class ToolRegistry:
    """Registry of tools available to agentic fluid particles."""
    def __init__(self):
        self.tools: Dict[str, AgentTool] = {}
        self._register_builtins()

    def register(self, tool: AgentTool):
        self.tools[tool.name] = tool

    def get_tool_inventory(self, tool_names: List[str] = None) -> str:
        t_list = tool_names if tool_names else list(self.tools.keys())
        return "\n".join([f"- {t}: {self.tools[t].description}" for t in t_list if t in self.tools])

    def _register_builtins(self):
        self.register(AgentTool("web_search", "Search the web.", lambda q: f"Web result for {q}"))
        self.register(AgentTool("database_search", "Search internal DB.", lambda cypher: f"DB result for {cypher}"))

class AgentGenerator:
    """Generate domain-expert agents from user context dynamically mapping JSON constraints."""
    def __init__(self, slm_client: SLMClient = None):
        self.slm_client = slm_client or SLMClient()

    def generate_team(self, context_chunk: str, team_size: int = 2) -> List[AgentSpec]:
        """Ask the local GPT4All instance to architect specialized agent experts natively."""
        prompt = (
            f"You are the Fluid System Architect.\n"
            f"Build a team of exactly {team_size} agents to solve this task: {context_chunk}\n"
            f"Allowed Tools: [web_search, database_search]\n"
            f"Reply STRICTLY in JSON. Format: {{\"agents\": [{{\"name\": \"AI_1\", \"domain\": \"...\", "
            f"\"description\": \"...\", \"system_prompt\": \"...\", \"tools\": [\"database_search\"]}}]}}"
        )
        
        response = self.slm_client.generate_json(context_chunk, prompt)
        agents_data = response.get("agents", [])
        
        if not agents_data:
            # Fallback deterministic stubs if the LLM hallucinated the JSON block completely.
            return [
                AgentSpec(
                    name=f"Expert_Fallback_{i}",
                    domain="Graph Analysis",
                    description="Specialist analyzing architecture natively.",
                    system_prompt="You are an expert. Use your bounded tools.",
                    tools=["database_search"]
                ) for i in range(team_size)
            ]
            
        agents = []
        for a in agents_data:
            agents.append(AgentSpec(
                name=a.get("name", "Unknown_Agent"),
                domain=a.get("domain", "General"),
                description=a.get("description", ""),
                system_prompt=a.get("system_prompt", ""),
                tools=a.get("tools", ["database_search"])
            ))
            
        return agents

class FluidEngine:
    """Simulates multi-agent propagation bridging LLM generation and state machines."""
    def __init__(self, tool_registry: ToolRegistry, generator: AgentGenerator):
        self.tool_registry = tool_registry
        self.generator = generator

    async def propagate_fluid(self, initial_query: str) -> AsyncGenerator[Dict, None]:
        """Propagate multiple agents asynchronously yielding dynamically driven JSON blocks."""
        yield {"status": "starting", "message": f"Fluid cascade computing logic for: {initial_query}"}
        
        team = self.generator.generate_team(initial_query, team_size=2)
        yield {"status": "team_generated", "agents": [a.name for a in team]}

        for agent in team:
            yield {"status": "agent_action", "agent": agent.name, "message": f"{agent.name} is assessing task priorities..."}
            
            tool_decider_prompt = (
                f"You are {agent.name}.\nSystem: {agent.system_prompt}\n"
                f"Your task: {initial_query}\n"
                f"Evaluate if you must dispatch an available tool: {agent.tools}\n"
                "Return exactly JSON format: {\"tool\": \"chosen_tool_name\"}"
            )
            
            decision = self.generator.slm_client.generate_json(initial_query, tool_decider_prompt)
            chosen_tool = decision.get("tool", "database_search")
            
            yield {"status": "tool_call", "agent": agent.name, "tool": chosen_tool}
            await asyncio.sleep(0.01) # Yield event loop
            
        yield {"status": "done", "message": "Fluid cascade complete."}
