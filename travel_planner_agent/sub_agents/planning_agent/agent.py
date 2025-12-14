"""Configures the planning agent instance."""

from google.adk.agents.llm_agent import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai.types import ThinkingConfig

from travel_planner_agent.sub_agents.planning_agent import prompt
from travel_planner_agent.tools.search import search_flight, search_hotel

thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=256)

planner = BuiltInPlanner(thinking_config=thinking_config)

planning_agent = Agent(
    model="gemini-2.5-flash",
    name="planning_agent",
    description="Specialist that collects requirements and drafts trip plans for travelers.",
    instruction=prompt.PLANNING_AGENT_INSTR,
    planner=planner,
    tools=[search_flight, search_hotel, google_search],
)
