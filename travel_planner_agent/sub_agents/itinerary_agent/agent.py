"""Configures the itinerary agent instance."""

from google.adk.agents.llm_agent import Agent

# from google.adk.models.lite_llm import LiteLlm

from travel_planner_agent.sub_agents.itinerary_agent import prompt
from travel_planner_agent.tools.mcp import AVAILABLE_MCP_TOOLSETS

itinerary_agent = Agent(
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.0-flash",
    name="itinerary_agent",
    description="Specialist that assembles confirmed travel details into shareable itineraries.",
    instruction=prompt.ITINERARY_AGENT_INSTR,
    tools=AVAILABLE_MCP_TOOLSETS,
)
