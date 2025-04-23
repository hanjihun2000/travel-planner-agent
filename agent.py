"""
An example of how to create a travel planner agent using the AGNO framework.
"""

import asyncio
import nest_asyncio

from os import getenv
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.json import JsonStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.playground import Playground, serve_playground_app

# MCP
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

# Tools
from agno.tools.duckduckgo import DuckDuckGoTools
# from agno.tools.thinking import ThinkingTools
from agno.tools.reasoning import ReasoningTools
from custom_tool import CustomSerpAPITools

import prompt

nest_asyncio.apply()

load_dotenv()
project_id = getenv('GOOGLE_CLOUD_PROJECT')
location = getenv('GOOGLE_CLOUD_LOCATION')
google_maps_api_key = getenv('GOOGLE_MAPS_API_KEY')

memory_db = SqliteMemoryDb(table_name="memory", db_file="assets/memory.db")
memory = Memory(db=memory_db)


async def run_server() -> None:
    if not google_maps_api_key:
        raise ValueError(
            "Please set the GOOGLE_MAPS_API_KEY environment variable.")

    env = {
        "GOOGLE_MAPS_API_KEY": google_maps_api_key,
    }

    # Initialize the MCP server
    airbnb_server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
    )

    maps_server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-google-maps"],
        env=env,
    )

    async with (
        MCPTools(server_params=airbnb_server_params) as airbnb_tools,
        MCPTools(server_params=maps_server_params) as google_maps_tools
    ):
        agent = Agent(
            name="Travel Planner Agent",
            memory=memory,
            enable_user_memories=True,
            storage=JsonStorage(dir_path="assets/agent_sessions_json"),
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
            ),
            tools=[
                # airbnb_tools,
                # google_maps_tools,
                DuckDuckGoTools(),
                ReasoningTools(add_instructions=True),
                CustomSerpAPITools(),
            ],
            show_tool_calls=True,
            description=prompt.description,
            instructions=prompt.instructions,
            expected_output=prompt.expected_output,
            monitoring=True,
            markdown=True,
            add_datetime_to_instructions=True,
            debug_mode=True,  # Enable debug mode for detailed logs, only for testing
        )

        playground = Playground(agents=[agent])
        app = playground.get_app()
        serve_playground_app(app)

if __name__ == "__main__":
    asyncio.run(run_server())
