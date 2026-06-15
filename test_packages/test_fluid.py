import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.agentic.fluid_engine import FluidEngine, ToolRegistry, AgentGenerator

async def main():
    reg = ToolRegistry()
    gen = AgentGenerator()
    engine = FluidEngine(reg, gen)

    print("🚀 Triggering Agentic Fluid Cascade for query: 'start fluid'")
    
    async for event in engine.propagate_fluid("start fluid"):
        if event["status"] == "starting":
            print(f"[{event['status']}] {event['message']}")
        elif event["status"] == "team_generated":
            print(f"[{event['status']}] Assembled Agents: {event['agents']}")
        elif event["status"] == "agent_action":
            print(f"   🤖 [{event['agent']}]: {event['message']}")
        elif event["status"] == "tool_call":
            print(f"   ⚙️ [{event['agent']}] invoked tool: '{event['tool']}'")
        elif event["status"] == "done":
            print(f"🏁 [{event['status']}] {event['message']}")
            
if __name__ == "__main__":
    asyncio.run(main())
