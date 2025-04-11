import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.json import JsonStorage


load_dotenv()
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
location = os.getenv('GOOGLE_CLOUD_LOCATION')

agent = Agent(
    storage=JsonStorage(dir_path="tmp/agent_sessions_json"),
    model=Gemini(
        id="gemini-2.0-flash-001",
        vertexai=True,
        project_id=project_id,
        location=location,
        search=True,
        show_tool_calls=True
    ),
    markdown=True,
    monitoring=True
)

agent.print_response(
    "Can you help me to search what are the events that are happening in Hong Kong that I can visit this weekend?")
