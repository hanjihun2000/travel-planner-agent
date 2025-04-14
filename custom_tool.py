import json
from os import getenv
from typing import Optional

from agno.tools import Toolkit
from agno.utils.log import log_info, logger

try:
    import serpapi
except ImportError:
    raise ImportError("`google-search-results` not installed.")


class CustomSerpAPITools(Toolkit):
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(name="custom_serpapi_tools", **kwargs)
        self.api_key = api_key or getenv("SERP_API_KEY")
        if not self.api_key:
            logger.warning("No Serpapi API key provided")
        self.register(self.search_flight)
        self.register(self.search_hotel)

    def search_flight(self, departure_id: str, arrival_id: str, outbound_date: str, return_date: Optional[str] = None, num_results: int = 3) -> str:
        """
        Search for flights using the Serpapi Google Flights API.

        Args:
            departure_id (str): IATA code of the departure airport (e.g., "JFK").
            arrival_id (str): IATA code of the arrival airport (e.g., "LAX").
            outbound_date (str): Departure date in YYYY-MM-DD format (e.g., "2023-12-25").
            return_date (Optional[str]): Return date in YYYY-MM-DD format for round trips (e.g., "2023-12-30").
            num_results (int): Number of best flights to return (default: 3).

        Returns:
            str: JSON string containing the top flight results or an error message.
                Keys:
                    - 'best_flights': List of the best flight options, limited to num_results.
                    - 'error': Error message if the search fails.
        """
        try:
            if not self.api_key:
                return json.dumps({"error": "Please provide an API key"})
            if not departure_id or not arrival_id or not outbound_date:
                return json.dumps({"error": "Please provide departure_id, arrival_id, and outbound_date"})

            log_info(
                f"Searching flights from {departure_id} to {arrival_id} on {outbound_date}")

            params = {
                "engine": "google_flights",
                "departure_id": departure_id,
                "arrival_id": arrival_id,
                "outbound_date": outbound_date,
                "currency": "HKD",  # Change to your preferred currency
                "hl": "en",
                "api_key": self.api_key
            }
            if return_date:
                params["return_date"] = return_date

            search = serpapi.GoogleSearch(params)
            results = search.get_dict()

            # Check for API errors
            if "error" in results:
                return json.dumps({"error": results["error"]})

            # Handle None by defaulting to an empty list
            filtered_results = {
                "best_flights": (results.get("best_flights") or [])[:num_results]
            }

            return json.dumps(filtered_results)

        except Exception as e:
            return json.dumps({"error": f"Error searching for flights: {e}"})

    def search_hotel(self, location: str, check_in_date: str, check_out_date: str, num_results: int = 3) -> str:
        """
        Search for hotels using the Serpapi Google Hotels API.

        Args:
            location (str): Location to search for hotels (e.g., "New York").
            check_in_date (str): Check-in date in YYYY-MM-DD format (e.g., "2023-12-25").
            check_out_date (str): Check-out date in YYYY-MM-DD format (e.g., "2023-12-30").
            num_results (int): Number of hotel properties to return (default: 3).

        Returns:
            str: JSON string containing the top hotel results or an error message.
                Keys:
                    - 'properties': List of hotel properties, limited to num_results.
                    - 'error': Error message if the search fails.
        """
        try:
            if not self.api_key:
                return json.dumps({"error": "Please provide an API key"})
            if not location or not check_in_date or not check_out_date:
                return json.dumps({"error": "Please provide location, check_in_date, and check_out_date"})

            log_info(
                f"Searching hotels in {location} from {check_in_date} to {check_out_date}")

            params = {
                "engine": "google_hotels",
                "q": location,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "adults": "2",  # Change to your preferred number of adults
                "currency": "HKD",  # Change to your preferred currency
                "hl": "en",
                "api_key": self.api_key
            }

            search = serpapi.GoogleSearch(params)
            results = search.get_dict()

            # Check for API errors
            if "error" in results:
                return json.dumps({"error": results["error"]})

            # Handle None by defaulting to an empty list
            filtered_results = {
                "properties": (results.get("properties") or [])[:num_results]
            }

            return json.dumps(filtered_results)

        except Exception as e:
            return json.dumps({"error": f"Error searching for hotels: {e}"})
