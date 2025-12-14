# Travel Planner Agent

> A multi-agent travel planning system built with Google ADK that coordinates flight/hotel search, booking simulation, and itinerary generation.

[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google)](https://github.com/google/generative-ai-dart)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](https://www.postgresql.org/)

## Overview

The Travel Planner Agent is an intelligent concierge system that uses a **hierarchical multi-agent architecture** to handle complex travel planning tasks. It decomposes the workflow into specialized roles:

1.  **Discovery**: Searching for flights and hotels (SerpAPI).
2.  **Booking**: Simulating payments and confirming reservations (PostgreSQL).
3.  **Itinerary**: Generating shareable trip summaries and calendars.

## Architecture

The system uses a **Root Agent** to coordinate three specialist sub-agents:

```mermaid
flowchart TD
    Root["Root Agent"] --> Planning["Planning Agent"]
    Root --> Booking["Booking Agent"]
    Root --> Itinerary["Itinerary Agent"]

    Planning --> Search["Search Tools"]
    Booking --> DB[("Payment DB")]
    Itinerary --> Files["Export Files"]
```

### Agent Roles

- **Root Agent**: The coordinator. Routes user requests to the appropriate specialist and maintains the overall trip context.
- **Planning Agent**: The researcher. Finds flights and hotels, compares options, and drafts the initial plan. **Always asks for user confirmation** before proceeding.
- **Booking Agent**: The executor. Handles payment simulation, generates PNRs/confirmation codes, and validates bookings.
- **Itinerary Agent**: The publisher. Formats the final trip details into a Markdown itinerary and `.ics` calendar file.

## Setup & Installation

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Google Cloud Project (for Vertex AI / Gemini API)
- SerpAPI Key (for real-time flight/hotel data)

### Installation

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/hanjihun2000/travel-planner-agent.git
    cd travel-planner-agent
    ```

2.  **Create a virtual environment**:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the Database**:

    ```bash
    createdb travel_payments
    ```

5.  **Configure Environment**:
    Create a `.env` file in the root directory:

    ```bash
    # Database
    PAYMENTS_DB_URL=postgresql://user:password@localhost:5432/travel_payments

    # APIs
    SERP_API_KEY=your_serpapi_key
    GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
    GOOGLE_CLOUD_PROJECT=your-project-id

    # Settings
    SERP_API_DEFAULT_CURRENCY=USD
    ```

## Usage

1.  **Start the Agent Server**:

    ```bash
    adk web
    ```

2.  **Access the UI**:
    Open `http://127.0.0.1:8000` in your browser.

3.  **Example Interaction**:
    > **User**: "Plan a trip to Tokyo for Dec 1-5."
    >
    > **Agent**: Searches for flights and hotels, presents options.
    >
    > **User**: "Looks good, book it."
    >
    > **Agent**: Simulates booking, generates confirmation codes, and provides a downloadable itinerary.

## Testing

Run the test suite to verify the agent configuration:

```bash
pytest tests/
```

## License

[MIT License](LICENSE)
