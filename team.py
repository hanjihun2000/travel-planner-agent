"""
Team of agents to plan a trip itinerary.
"""

import asyncio
import nest_asyncio
from os import getenv
from dotenv import load_dotenv
from textwrap import dedent
from typing import List, Optional
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.json import JsonStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools
from mcp import StdioServerParameters
from pydantic import BaseModel
from agno.playground import Playground, serve_playground_app
from custom_tool import CustomSerpAPITools
import prompt


load_dotenv()
project_id = getenv('GOOGLE_CLOUD_PROJECT')
location = getenv('GOOGLE_CLOUD_LOCATION')
google_maps_api_key = getenv('GOOGLE_MAPS_API_KEY')

team_memory_db = SqliteMemoryDb(
    table_name="memory", db_file="assets/team_memory.db")
memory = Memory(db=team_memory_db)

nest_asyncio.apply()

# Define response models


class AirbnbListing(BaseModel):
    name: str
    description: str
    address: Optional[str] = None
    price: Optional[str] = None
    dates_available: Optional[List[str]] = None
    url: Optional[str] = None


class Attraction(BaseModel):
    name: str
    description: str
    location: str
    rating: Optional[float] = None
    visit_duration: Optional[str] = None
    best_time_to_visit: Optional[str] = None


class WeatherInfo(BaseModel):
    average_temperature: str
    precipitation: str
    recommendations: str


class TravelPlan(BaseModel):
    airbnb_listings: List[AirbnbListing]
    attractions: List[Attraction]
    weather_info: Optional[WeatherInfo] = None
    suggested_itinerary: Optional[List[str]] = None


async def run_team() -> None:
    if not google_maps_api_key:
        raise ValueError(
            "Please set the GOOGLE_MAPS_API_KEY environment variable.")

    env = {
        "GOOGLE_MAPS_API_KEY": google_maps_api_key,
    }
    # Define server parameters
    airbnb_server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
    )

    maps_server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-google-maps"],
        env=env,
    )

    # Use AsyncExitStack to manage multiple context managers
    async with (
        MCPTools(server_params=airbnb_server_params) as airbnb_tools,
        MCPTools(server_params=maps_server_params) as maps_tools,
    ):
        # Create all agents
        airbnb_agent = Agent(
            name="Airbnb",
            role="Airbnb Agent",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[airbnb_tools],
            instructions=dedent("""\
                You are an agent that can find Airbnb listings for a given location and date.\
                Make sure to response back the top 3 Airbnb accommodations, including the price, description, address, and dates available.\
            """),
            memory=memory,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
        )

        location_service_agent = Agent(
            name="Location Service",
            role="Location Service Agent",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[maps_tools],
            instructions=dedent("""\
                You are an agent that provides location services, directions and place details through Google Maps MCP tools.\
                Use your ability to help planning travel routes and find interesting places to visit for a given location and date.\
            """),
            memory=memory,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
        )

        web_search_agent = Agent(
            name="Web Search",
            role="Web Search Agent",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[DuckDuckGoTools(cache_results=True)],
            instructions=dedent("""\
                You are an agent that can search the web for information.\
                Search for information about a given location and date.\
            """),
            memory=memory,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
        )

        weather_search_agent = Agent(
            name="Weather Search",
            role="Weather Search Agent",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[DuckDuckGoTools()],
            instructions=dedent("""\
                You are an agent that can search the web for information.\
                Search for the weather forecast for a given location and date.\
            """),
            memory=memory,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
        )

        flight_hotel_agent = Agent(
            name="Flight and Hotel Search",
            role="Flight and Hotel Search Agent",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[CustomSerpAPITools()],
            instructions=dedent("""\
                You are an agent that can search for flights and hotels.\
                Search for flights and hotels for a given location and date.\
                Make sure to include the top 3 flights and hotels, including the price, description, address, and dates available.\
            """),
            memory=memory,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
        )

        # Create and run the team
        team = Team(
            name="Travel Planner Team",
            team_id="travel_planner_team",
            mode="coordinate",
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            members=[
                # airbnb_agent,
                # weather_search_agent,
                web_search_agent,
                location_service_agent,
                flight_hotel_agent,
            ],
            instructions=[
                "Plan a full itinerary for the trip that user want to go.",
                "Continue asking individual team members until you have ALL the information you need.",
                "Think about the best way to tackle the task.",
                "You have three members that you can coordinate: {web_search_agent}, {location_service_agent}, and {flight_hotel_agent}.",
                "{web_search_agent} is capable of searching for destination information, such as famous places to visit and events that will be held during the travel period.",
                "{location_service_agent} is capable of providing directions from one place to the another place and finding detail information of interesting places to visit after {web_search_agent} searching.",
                "{flight_hotel_agent} is capable of finding for flights and hotels given a location and date.",
            ],
            tools=[ReasoningTools(add_instructions=True)],
            # response_model=TravelPlan,
            enable_agentic_context=True,
            enable_user_memories=True,
            memory=memory,
            storage=JsonStorage(dir_path="assets/team_sessions_json"),
            show_tool_calls=True,
            markdown=True,
            # debug_mode=True,
            show_members_responses=True,
            add_datetime_to_instructions=True,
            success_criteria="The team has successfully plan a trip itinerary for a given location and date.",
            monitoring=True,
            expected_output=prompt.expected_output,
        )

        # # Execute the team's task
        # await team.aprint_response(
        #     dedent("""\
        #     I want to travel to San Francisco from New York sometime in May.
        #     I am one person going for 2 weeks.
        #     Plan my travel itinerary.
        #     Make sure to include the best attractions, restaurants, and activities.
        #     Make sure to include the best Airbnb listings.
        #     Make sure to include the weather information.\
        # """)
        # )

        playground = Playground(teams=[team])
        app = playground.get_app()
        serve_playground_app(app)


if __name__ == "__main__":
    asyncio.run(run_team())
