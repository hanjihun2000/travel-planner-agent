# Travel Planner Agent

Travel Planner Agent is an advanced AI-powered travel planning assistant built using the [Agno AI framework](https://github.com/agno-agi/agno/tree/main). It leverages cutting-edge tools like Google Gemini and SerpAPI to provide personalized travel itineraries, accommodation recommendations, and activity suggestions. This project is designed to help users plan their trips efficiently and effectively, making travel planning a breeze.

## Features

- **Flight Search**: Find the best flights using SerpAPI's Google Flights engine.
- **Hotel Search**: Discover top-rated hotels using SerpAPI's Google Hotels engine.
- **Customizable Itineraries**: Generate detailed day-by-day travel plans.
- **Multi-Tool Integration**: Includes DuckDuckGo and custom SerpAPI tools for enhanced search capabilities.

---

## Installation

### Prerequisites

- Python 3.8 or higher
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (optional, for Google Gemini integration)
- [SerpAPI Key](https://serpapi.com/) (for flight and hotel searches)

### Steps

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file (or copy `.env.example` file) in the root directory with the following keys:

   ```env
   GOOGLE_CLOUD_PROJECT=<your-google-cloud-project-id>
   GOOGLE_CLOUD_LOCATION=<your-google-cloud-location>
   GOOGLE_GENAI_USE_VERTEXAI="true"
   SERP_API_KEY=<your-serpapi-key>
   ```

   **Note**: Do not commit your `.env` file to version control. It is ignored by `.gitignore` for security.

---

## Usage

1. Run the agent:

   ```bash
   python agent.py
   ```

2. The agent will initialize with the following tools:

   - **DuckDuckGoTools**: For general web searches.
   - **ThinkingTools**: For advanced reasoning and planning.
   - **CustomSerpAPITools**: For flight and hotel searches.

3. Interact with the agent to generate travel plans and itineraries.

---

## Environment Variables

The project requires the following environment variables to function:

| Key                         | Description                                                    |
| --------------------------- | -------------------------------------------------------------- |
| `GOOGLE_CLOUD_PROJECT`      | Your Google Cloud project ID.                                  |
| `GOOGLE_CLOUD_LOCATION`     | The location of your Google Cloud resources.                   |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `"true"` to enable Vertex AI integration.               |
| `SERP_API_KEY`              | Your SerpAPI key for accessing Google Flights and Hotels APIs. |

---

## Tools and Frameworks

- **[Agno AI Framework](https://github.com/agno-agi/agno/tree/main)**: A modular framework for building AI agents.
- **[Google Gemini](https://docs.agno.com/models/google)**: A powerful language model for advanced reasoning and planning.
- **[DuckDuckGo](https://duckduckgo.com/)**: A privacy-focused search engine for general web searches.
- **[SerpAPI](https://serpapi.com/)**: A real-time API for accessing search engine results, including Google Flights and Hotels.
- **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)**: Command-line tools for managing Google Cloud resources.
- **[Vertex AI](https://cloud.google.com/vertex-ai)**: A managed machine learning platform for building and deploying AI models.

---

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
