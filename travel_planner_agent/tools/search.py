"""Search tools for travel planner agent.

Provides functions to search for flights, hotels, and general web information.
"""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    import serpapi
except ImportError:
    serpapi = None


def _require_serpapi_key() -> Optional[str]:
    return os.getenv("SERP_API_KEY")


def search_flight(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str] = None,
    num_results: int = 5,
) -> dict[str, Any]:
    """Search for flights via SerpAPI Google Flights.

    Args:
        departure_id: IATA code for the departure airport (for example, "SFO").
        arrival_id: IATA code for the arrival airport (for example, "LHR").
        outbound_date: Outbound travel date formatted as "YYYY-MM-DD".
        return_date: Optional return date formatted as "YYYY-MM-DD".
        num_results: Maximum number of itineraries to include in the response.

    Returns:
        A dictionary with status and either best_flights containing the
        truncated list of itineraries returned by SerpAPI or error_message
        when the lookup fails.
    """
    api_key = _require_serpapi_key()
    if serpapi is None:
        return {"status": "error", "error_message": "serpapi package not installed"}
    if not api_key:
        return {"status": "error", "error_message": "serp api key missing"}
    if not (departure_id and arrival_id and outbound_date):
        return {
            "status": "error",
            "error_message": "departure_id, arrival_id, outbound_date required",
        }
    try:
        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "currency": "HKD",  # TODO: change to local currency based on user location
            "hl": "en",
            "api_key": api_key,
        }
        if return_date:
            params["return_date"] = return_date
        results = serpapi.GoogleSearch(params).get_dict()
        if "error" in results:
            return {"status": "error", "error_message": results["error"]}
        best_flights = (results.get("best_flights") or [])[: num_results or 5]
        return {"status": "success", "best_flights": best_flights}
    except Exception as e:
        return {"status": "error", "error_message": f"flight search failed: {e}"}


def search_hotel(
    location: str,
    check_in_date: str,
    check_out_date: str,
    adults: str = "2",
    children: str = "0",
    num_results: int = 5,
) -> dict[str, Any]:
    """Search for hotels via SerpAPI Google Hotels.

    Args:
        location: Destination name or locality to search for accommodation.
        check_in_date: Check-in date formatted as "YYYY-MM-DD".
        check_out_date: Check-out date formatted as "YYYY-MM-DD".
        adults: Number of adults encoded as a string per SerpAPI requirements.
        children: Number of children encoded as a string per SerpAPI requirements.
        num_results: Maximum number of hotel properties to include in the result.

    Returns:
        A dictionary with status and either properties containing hotel
        metadata returned by SerpAPI or error_message if the lookup fails.
    """
    api_key = _require_serpapi_key()
    if serpapi is None:
        return {"status": "error", "error_message": "serpapi package not installed"}
    if not api_key:
        return {"status": "error", "error_message": "serp api key missing"}
    if not (location and check_in_date and check_out_date):
        return {
            "status": "error",
            "error_message": "location, check_in_date, check_out_date required",
        }
    try:
        params = {
            "engine": "google_hotels",
            "q": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "children": children,
            "currency": "HKD",  # TODO: change to local currency based on user location
            "hl": "en",
            "api_key": api_key,
        }
        results = serpapi.GoogleSearch(params).get_dict()
        if "error" in results:
            return {"status": "error", "error_message": results["error"]}
        props = (results.get("properties") or [])[: num_results or 5]
        return {"status": "success", "properties": props}
    except Exception as e:
        return {"status": "error", "error_message": f"hotel search failed: {e}"}


def web_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Retrieve quick destination summaries using DuckDuckGo Instant Answer.

    Args:
        query: Free-form search query describing the destination or topic.
        num_results: Maximum number of related snippets to include.

    Returns:
        A dictionary with status and either abstract plus related
        snippets or error_message if the request fails.
    """
    import urllib.parse
    import urllib.request
    import json as _json

    base = "https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&q="
    try:
        url = base + urllib.parse.quote(query)
        with urllib.request.urlopen(url, timeout=8) as response:
            data = _json.loads(response.read().decode("utf-8"))
        abstract = data.get("AbstractText") or data.get("Abstract") or ""
        related_raw = data.get("RelatedTopics") or []
        related = []
        for item in related_raw:
            if isinstance(item, dict) and item.get("Text"):
                related.append(item["Text"])
            if len(related) >= num_results:
                break
        return {"status": "success", "abstract": abstract, "related": related}
    except Exception as e:
        return {"status": "error", "error_message": f"web search failed: {e}"}
