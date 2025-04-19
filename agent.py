import asyncio
import nest_asyncio

from os import getenv
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.google import Gemini

# Session and Memory
from agno.storage.json import JsonStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.playground import Playground, serve_playground_app

# MCP
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

# Tools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools
from custom_tool import CustomSerpAPITools

# import prompt
import prompt

nest_asyncio.apply()

load_dotenv()
project_id = getenv('GOOGLE_CLOUD_PROJECT')
location = getenv('GOOGLE_CLOUD_LOCATION')

memory_db = SqliteMemoryDb(table_name="memory", db_file="assets/memory.db")
memory = Memory(db=memory_db)


async def run_server() -> None:
    # Initialize the MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
    )

    async with MCPTools(server_params=server_params) as mcp_tools:
        agent = Agent(
            name="Travel Planner Agent",
            memory=memory,
            storage=JsonStorage(dir_path="assets/agent_sessions_json"),
            model=Gemini(
                id="gemini-2.0-flash-001",
                vertexai=True,
                project_id=project_id,
                location=location,
                # search=True, # Enable Gemini's built-in search tool
                show_tool_calls=True
            ),
            tools=[
                mcp_tools,
                DuckDuckGoTools(),
                ReasoningTools(add_instructions=True),
                CustomSerpAPITools(),
            ],
            show_tool_calls=True,
            description=prompt.description,
            instructions=prompt.instructions,
            expected_output=prompt.expected_output,
            markdown=True,
            monitoring=True,
            enable_user_memories=True,
            add_datetime_to_instructions=True,
            # add_history_to_messages=True,
            # num_history_responses=3,
            # read_chat_history=True,
            # read_tool_call_history=True,
            # debug_mode=True,
            stream_intermediate_steps=True,
        )

        playground = Playground(agents=[agent])
        app = playground.get_app()
        serve_playground_app(app)

if __name__ == "__main__":
    asyncio.run(run_server())
