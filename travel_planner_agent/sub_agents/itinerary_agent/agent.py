"""Configures the itinerary agent instance."""

from google.adk.agents.llm_agent import Agent

from travel_planner_agent.sub_agents.itinerary_agent import prompt
from travel_planner_agent.tools.mcp import AVAILABLE_MCP_TOOLSETS

itinerary_agent = Agent(
    model="gemini-2.5-flash",
    name="itinerary_agent",
    description="Specialist that assembles confirmed travel details into shareable itineraries.",
    instruction=prompt.ITINERARY_AGENT_INSTR,
    tools=AVAILABLE_MCP_TOOLSETS,
)
