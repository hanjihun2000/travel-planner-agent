from google.adk.agents.llm_agent import Agent
from travel_planner_agent import prompt

# from google.adk.models.lite_llm import LiteLlm
# from os import getenv

from travel_planner_agent.sub_agents.itinerary_agent import itinerary_agent
from travel_planner_agent.sub_agents.booking_agent import booking_agent
from travel_planner_agent.sub_agents.planning_agent import planning_agent


root_agent = Agent(
    # For local testing with Ollama LLM
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.0-flash",
    name="root_agent",
    description="Coordinator that routes travel requests to planning, booking, and itinerary specialist agents.",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[planning_agent, booking_agent, itinerary_agent],
)
