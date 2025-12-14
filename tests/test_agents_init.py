from google.adk.agents.llm_agent import Agent
from travel_planner_agent.agent import create_root_agent, root_agent
from travel_planner_agent.sub_agents.planning_agent.agent import planning_agent
from travel_planner_agent.sub_agents.booking_agent.agent import booking_agent
from travel_planner_agent.sub_agents.itinerary_agent.agent import itinerary_agent


def test_agents_initialization():
    """Verify that all agents are initialized correctly."""
    assert planning_agent is not None
    assert planning_agent.name == "planning_agent"

    assert booking_agent is not None
    assert booking_agent.name == "booking_agent"

    assert itinerary_agent is not None
    assert itinerary_agent.name == "itinerary_agent"


def test_create_root_agent_factory():
    """Verify that the factory creates a root agent with provided sub-agents."""
    # Create dummy sub-agents for testing the factory
    dummy_planning = Agent(model="test-model", name="planning", instruction="test")
    dummy_booking = Agent(model="test-model", name="booking", instruction="test")
    dummy_itinerary = Agent(model="test-model", name="itinerary", instruction="test")

    agent = create_root_agent(dummy_planning, dummy_booking, dummy_itinerary)

    assert agent is not None
    assert agent.name == "root_agent"
    assert len(agent.sub_agents) == 3
    assert agent.sub_agents[0] == dummy_planning
    assert agent.sub_agents[1] == dummy_booking
    assert agent.sub_agents[2] == dummy_itinerary


def test_global_root_agent():
    """Verify the global root agent is configured with the real sub-agents."""
    assert root_agent is not None
    assert root_agent.name == "root_agent"
    assert len(root_agent.sub_agents) == 3
    # Check that the real sub-agents are attached
    assert planning_agent in root_agent.sub_agents
    assert booking_agent in root_agent.sub_agents
    assert itinerary_agent in root_agent.sub_agents
