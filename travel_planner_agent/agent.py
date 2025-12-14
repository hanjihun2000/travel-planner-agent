"""Configures the root agent instance."""

from google.adk.agents.llm_agent import Agent
from travel_planner_agent import prompt

from travel_planner_agent.sub_agents.itinerary_agent import itinerary_agent
from travel_planner_agent.sub_agents.booking_agent import booking_agent
from travel_planner_agent.sub_agents.planning_agent import planning_agent
from travel_planner_agent.session_state import register_session_callbacks


def create_root_agent(
    planning_agent: Agent, booking_agent: Agent, itinerary_agent: Agent
) -> Agent:
    """Creates and configures the root agent with its sub-agents."""
    agent = Agent(
        model="gemini-2.5-flash",
        name="root_agent",
        description="Coordinator that routes travel requests to planning, booking, and itinerary specialist agents.",
        instruction=prompt.ROOT_AGENT_INSTR,
        sub_agents=[planning_agent, booking_agent, itinerary_agent],
    )
    register_session_callbacks(agent)
    return agent


root_agent = create_root_agent(planning_agent, booking_agent, itinerary_agent)
