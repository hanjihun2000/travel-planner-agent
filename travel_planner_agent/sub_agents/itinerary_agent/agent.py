"""Configures the itinerary agent instance."""

from google.adk.agents.llm_agent import Agent

# from google.adk.models.lite_llm import LiteLlm

from travel_planner_agent.sub_agents.itinerary_agent import prompt

itinerary_agent = Agent(
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.0-flash",
    name="itinerary_agent",
    description="Specialist that assembles confirmed travel details into shareable itineraries.",
    instruction=prompt.ITINERARY_AGENT_INSTR,
)
