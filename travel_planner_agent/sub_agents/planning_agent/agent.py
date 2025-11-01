"""Configures the planning agent instance."""

from google.adk.agents.llm_agent import Agent

# from google.adk.models.lite_llm import LiteLlm

from travel_planner_agent.sub_agents.planning_agent import prompt

planning_agent = Agent(
    # model=LiteLlm(model=f"{getenv('OLLAMA_MODEL_ID', 'ollama_chat/qwen3:8b')}"),
    model="gemini-2.0-flash",
    name="planning_agent",
    description="Specialist that collects requirements and drafts trip plans for travelers.",
    instruction=prompt.PLANNING_AGENT_INSTR,
)
