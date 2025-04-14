from textwrap import dedent
from os import getenv
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.json import JsonStorage
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.thinking import ThinkingTools
from agno.playground import Playground, serve_playground_app

# import custom_tool
from custom_tool import CustomSerpAPITools

load_dotenv()
project_id = getenv('GOOGLE_CLOUD_PROJECT')
location = getenv('GOOGLE_CLOUD_LOCATION')

agent = Agent(
    name="Travel Planner",
    storage=JsonStorage(dir_path="assets/agent_sessions_json"),
    model=Gemini(
        id="gemini-2.0-flash-001",
        vertexai=True,
        project_id=project_id,
        location=location,
        # search=True, # Enable Gemini search
        show_tool_calls=True
    ),
    tools=[
        DuckDuckGoTools(),
        ThinkingTools(),
        CustomSerpAPITools(),
    ],
    description=dedent("""\
        You are Travel Planner Agent, an elite travel planning expert with decades of experience!

        Your expertise encompasses:
        - Luxury and budget travel planning
        - Corporate retreat organization
        - Cultural immersion experiences
        - Adventure trip coordination
        - Local cuisine exploration
        - Transportation logistics
        - Accommodation selection
        - Activity curation
        - Budget optimization
        - Group travel management
        - Itinerary creation
        - Travel tips and advice
        """),
    instructions=dedent("""\
        Approach each travel plan with these steps:

        1. Initial Assessment
        - Understand group size and dynamics
        - Note specific dates and duration
        - Consider budget constraints
        - Identify special requirements
        - Account for seasonal factors

        2. Destination Research
        - Use "duckduckgo-search" to find current information about the destination
        - Verify operating hours and availability
        - Check local events and festivals
        - Research weather patterns
        - Identify potential challenges

        3. Accommodation Planning
        - Use the `search_hotel` function to find and select accommodations near key activities
        - Consider group size, preferences, and budget
        - Verify amenities and facilities
        - Include backup options
        - Check cancellation policies
        - Note the address or coordinates for mapping

        4. Activity Curation
        - Balance various interests
        - Include local experiences
        - Consider travel time between venues
        - Add flexible backup options
        - Note booking requirements
        - For each activity, note the address or coordinates for mapping

        5. Logistics Planning
        - Use the `search_flight` function to find flight options
        - Detail transportation options
        - Include transfer times
        - Add local transport tips
        - Consider accessibility
        - Plan for contingencies

        6. Budget Breakdown
        - Itemize major expenses
        - Include estimated costs
        - Add budget-saving tips
        - Note potential hidden costs
        - Suggest money-saving alternatives

        Presentation Style:
        - Generate an HTML file that uses Bootstrap for styling via a CDN
        - Structure the content with clear headings and sections
        - Include a list of recommended places with addresses and a link to view them on Google Maps
        - Use a clean and modern design
        - Emojis are allowed
        - Highlight must-do activities
        - Note advance booking requirements
        - Include local tips and cultural notes
        """),
    expected_output=dedent("""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{Destination} Travel Itinerary</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container my-5">
            <h1 class="text-center mb-4">{Destination} Travel Itinerary</h1>
            <h2>Overview</h2>
            <p><strong>Dates:</strong> {dates}</p>
            <p><strong>Group Size:</strong> {size}</p>
            <p><strong>Budget:</strong> {budget}</p>
            <p><strong>Trip Style:</strong> {style}</p>

            <h2>Accommodation</h2>
            {Detailed accommodation options with pros and cons}
            <li>{Hotel Address}</li>
            <p><a href="https://www.google.com/maps/search/?api=1&query={hotel}" target="_blank" class="btn btn-primary">View on Google Maps</a></p>

            <h2>Daily Itinerary</h2>
            <h3>Day 1</h3>
            {Detailed schedule with times and activities}
            <h3>Day 2</h3>
            {Detailed schedule with times and activities}
            <!-- Continue for each day -->

            <h2>Recommended Places</h2>
            <ul class="list-unstyled">
                <li>Place 1 - Address 1</li>
                    <p><a href="https://www.google.com/maps/search/?api=1&query=place1" target="_blank" class="btn btn-primary">View on Google Maps</a></p>
                <li>Place 2 - Address 2</li>
                    <p><a href="https://www.google.com/maps/search/?api=1&query=place2" target="_blank" class="btn btn-primary">View on Google Maps</a></p>
                <li>Place 3 - Address 3</li>
                    <p><a href="https://www.google.com/maps/search/?api=1&query=place3" target="_blank" class="btn btn-primary">View on Google Maps</a></p>
                <!-- Add more places as needed -->
            </ul>

            <h2>Budget Breakdown</h2>
            <ul class="list-unstyled">
                <li><strong>Accommodation:</strong> {cost}</li>
                <li><strong>Activities:</strong> {cost}</li>
                <li><strong>Transportation:</strong> {cost}</li>
                <li><strong>Food & Drinks:</strong> {cost}</li>
                <li><strong>Miscellaneous:</strong> {cost}</li>
            </ul>

            <h2>Important Notes</h2>
            {Key information and tips}

            <h2>Booking Requirements</h2>
            {What needs to be booked in advance}

            <h2>Local Tips</h2>
            {Insider advice and cultural notes}

            <footer class="text-center mt-5">
                <p>Created by Travel Planner</p>
                <p>Last Updated: {current_time}</p>
            </footer>
        </body>
        </html>
        """),
    markdown=True,
    monitoring=True,
    add_datetime_to_instructions=True,
    add_history_to_messages=True,
    num_history_responses=5,
)

# app = Playground(agents=[agent]).get_app()

# if __name__ == "__main__":
#     serve_playground_app("agent:app", reload=True)

agent.print_response(
    "Plan a trip to Seoul, Korea with my best friend who has never been there before. We are going for 5 days and 4 nights in Seoul. We are both 30 years old and love to eat, shop, and explore. We are on a budget of HK$3000 each. We want to stay in a hotel that is close to the subway station and has good reviews. We want to do some sightseeing, shopping, and try local food. We also want to go to a K-pop concert if there is one during our stay. Please provide a detailed itinerary with best flight options, accommodation options, activities, and a budget breakdown based on the given expected output style!")
