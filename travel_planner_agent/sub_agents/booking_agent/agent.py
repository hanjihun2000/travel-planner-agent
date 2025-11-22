"""Configures the booking agent instance."""

from google.adk.agents.llm_agent import Agent

# from google.adk.models.lite_llm import LiteLlm

from travel_planner_agent.sub_agents.booking_agent import prompt
from travel_planner_agent.tools.mcp import AVAILABLE_MCP_TOOLSETS

booking_agent = Agent(
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.5-flash",
    name="booking_agent",
    description="Specialist that manages pricing validation and travel reservations for the user.",
    instruction=prompt.BOOKING_AGENT_INSTR,
    tools=AVAILABLE_MCP_TOOLSETS,
)
