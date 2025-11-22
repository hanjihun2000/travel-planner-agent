"""Configures the planning agent instance."""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search

# from google.adk.models.lite_llm import LiteLlm

from travel_planner_agent.sub_agents.planning_agent import prompt
from travel_planner_agent.tools.search import search_flight, search_hotel

# search_web

planning_agent = Agent(
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.5-flash",
    name="planning_agent",
    description="Specialist that collects requirements and drafts trip plans for travelers.",
    instruction=prompt.PLANNING_AGENT_INSTR,
    tools=[search_flight, search_hotel, google_search],
)
