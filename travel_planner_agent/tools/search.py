"""Search tools for travel planner agent.

Provides functions to search for flights, hotels, and general web information
while respecting the user's preferred currency and a conservative retry policy.
"""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Iterable, Optional


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(1, parsed)


SERP_API_MAX_ATTEMPTS = _env_int("SERP_API_MAX_ATTEMPTS", 1)
DEFAULT_SERP_CURRENCY = (os.getenv("SERP_API_DEFAULT_CURRENCY") or "USD").upper()

try:
    import serpapi
except ImportError:
    serpapi = None


def _require_serpapi_key() -> Optional[str]:
    return os.getenv("SERP_API_KEY")


def _resolve_currency(currency: Optional[str]) -> str:
    """Return an uppercase currency code with sane fallback."""

    value = (
        currency or os.getenv("TRAVEL_DEFAULT_CURRENCY") or DEFAULT_SERP_CURRENCY
    ).strip()
    return value.upper() or DEFAULT_SERP_CURRENCY


def _execute_serpapi_search(params: dict[str, Any]) -> dict[str, Any]:
    """Run a SerpAPI query with a capped number of attempts."""

    last_error: Exception | None = None
    for attempt in range(SERP_API_MAX_ATTEMPTS):
        try:
            return serpapi.GoogleSearch(params).get_dict()
        except Exception as exc:  # pragma: no cover - serpapi network dependency
            last_error = exc
            if attempt == SERP_API_MAX_ATTEMPTS - 1:
                raise
    raise last_error  # pragma: no cover - defensive guard


def _serialize_many(
    value: Optional[Iterable[Any] | str | int | float],
) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float)):
        return str(value)
    items = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    if not items:
        return None
    return ",".join(items)


def _serialize_simple(value: Optional[int | float | str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def search_flight(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str,
    num_results: int = 3,
    currency: Optional[str] = None,
) -> dict[str, Any]:
    """Search for flights via SerpAPI Google Flights.

    Args:
        departure_id: IATA code for the departure airport (for example, "SFO").
        arrival_id: IATA code for the arrival airport (for example, "LHR").
        outbound_date: Outbound travel date formatted as "YYYY-MM-DD".
        return_date: Return travel date formatted as "YYYY-MM-DD". Since this is a round-trip search, this parameter is required.
        num_results: Maximum number of itineraries to include in the response. Defaults to top 3.
        currency: Optional ISO 4217 code to quote results in. Defaults to ``SERP_API_DEFAULT_CURRENCY`` or ``USD`` if unset.

    Returns:
        A dictionary with ``status``. On success, ``best_flights`` contains the
        selected outbound itineraries enriched with ``return_best_flights`` when
        available. ``other_flights`` and ``price_insights`` are included when
        provided by SerpAPI. On failure, ``error_message`` describes the issue.
    """
    api_key = _require_serpapi_key()
    if serpapi is None:
        return {"status": "error", "error_message": "serpapi package not installed"}
    if not api_key:
        return {"status": "error", "error_message": "Serp API key missing"}
    if not (departure_id and arrival_id and outbound_date):
        return {
            "status": "error",
            "error_message": "departure_id, arrival_id, outbound_date required",
        }
    if not return_date:
        return {
            "status": "error",
            "error_message": "return_date required for round-trip flight search",
        }
    base_params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": _resolve_currency(currency),
        "hl": "en",
        "api_key": api_key,
        # TODO: expose optional parameters (bags, travel_class, etc.) through function arguments
        "bags": "1",
    }

    try:
        results = _execute_serpapi_search(base_params)
        if "error" in results:
            return {"status": "error", "error_message": results["error"]}

        outbound_candidates = (results.get("best_flights") or [])[:num_results]
        enriched_outbound: list[dict[str, Any]] = []
        return_queries = 0
        for flight in outbound_candidates:
            enriched = deepcopy(flight)
            token = flight.get("departure_token")
            if token and return_queries < num_results:
                return_data = _fetch_return_flights(base_params, token, num_results)
                if return_data["status"] == "success":
                    enriched["return_best_flights"] = return_data.get(
                        "best_flights", []
                    )
                    # if return_data.get("other_flights"):
                    #     enriched["return_other_flights"] = return_data["other_flights"]
                else:
                    enriched["return_error"] = return_data["error_message"]
                return_queries += 1
            elif token is None:
                enriched["return_warning"] = (
                    "departure_token not provided; unable to fetch return flights"
                )
            enriched_outbound.append(enriched)

        payload: dict[str, Any] = {
            "status": "success",
            "best_flights": enriched_outbound,
        }
        # TODO: ignore other_flights at this moment to not dump too many info to sub-agents
        # other_flights = results.get("other_flights") or []
        # if other_flights:
        #     payload["other_flights"] = other_flights[:num_results]
        price_insights = results.get("price_insights")
        if price_insights:
            payload["price_insights"] = price_insights
        return payload
    except Exception as e:
        return {"status": "error", "error_message": f"flight search failed: {e}"}


def _fetch_return_flights(
    base_params: dict[str, Any], departure_token: str, num_results: int
) -> dict[str, Any]:
    """Retrieve return leg options using SerpAPI's departure_token."""

    params = {**base_params, "departure_token": departure_token}
    try:
        data = _execute_serpapi_search(params)
    except Exception as exc:  # pragma: no cover - network dependency
        return {
            "status": "error",
            "error_message": f"return flight search failed: {exc}",
        }

    if "error" in data:
        return {"status": "error", "error_message": data["error"]}

    return {
        "status": "success",
        "best_flights": (data.get("best_flights") or [])[:num_results],
        "other_flights": (data.get("other_flights") or [])[:num_results],
    }


def search_hotel(
    location: str,
    check_in_date: str,
    check_out_date: str,
    adults: str = "1",
    children: str = "0",
    num_results: int = 3,
    currency: Optional[str] = None,
    sort_by: Optional[str] = None,
    min_price: Optional[str] = None,
    max_price: Optional[str] = None,
    property_types: Optional[str] = None,
    amenities: Optional[str] = None,
    rating: Optional[str] = None,
    hotel_class: Optional[str] = None,
) -> dict[str, Any]:
    """Search for hotels via SerpAPI Google Hotels.

    Args:
        location: Destination name or locality to search for accommodation.
        check_in_date: Check-in date formatted as "YYYY-MM-DD".
        check_out_date: Check-out date formatted as "YYYY-MM-DD".
        adults: Number of adults encoded as a string per SerpAPI requirements.
        children: Number of children encoded as a string per SerpAPI requirements.
        num_results: Maximum number of hotel properties to include in the result.
        currency: Optional ISO 4217 code to quote nightly rates in. Defaults to ``SERP_API_DEFAULT_CURRENCY`` or ``USD`` if unset.
        sort_by: Optional numeric sort identifier (for example, ``"3"`` for lowest price).
        min_price: Optional lower bound for nightly pricing.
        max_price: Optional upper bound for nightly pricing.
        property_types: Optional property type filter (comma-separated ids).
        amenities: Optional amenity filter (comma-separated ids).
        rating: Optional overall rating threshold (for example, ``"8"`` for 4.0+).
        hotel_class: Optional hotel class filter (comma-separated star values).

    Returns:
        A dictionary with status and either ``properties`` containing hotel
        metadata returned by SerpAPI or ``error_message`` if the lookup fails.
    """
    api_key = _require_serpapi_key()
    if serpapi is None:
        return {"status": "error", "error_message": "serpapi package not installed"}
    if not api_key:
        return {"status": "error", "error_message": "Serp API key missing"}
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
            "currency": _resolve_currency(currency),
            "hl": "en",
            "api_key": api_key,
        }

        optional_params = {
            "sort_by": _serialize_simple(sort_by),
            "min_price": _serialize_simple(min_price),
            "max_price": _serialize_simple(max_price),
            "property_types": _serialize_many(property_types),
            "amenities": _serialize_many(amenities),
            "rating": _serialize_simple(rating),
            "hotel_class": _serialize_many(hotel_class),
        }

        for key, value in optional_params.items():
            if value is not None:
                params[key] = value

        results = _execute_serpapi_search(params)
        if "error" in results:
            return {"status": "error", "error_message": results["error"]}
        props = (results.get("properties") or [])[: num_results or 5]
        return {"status": "success", "properties": props}
    except Exception as e:
        return {"status": "error", "error_message": f"hotel search failed: {e}"}


# Deprecated: use google-search instead
def search_web(query: str, num_results: int = 5) -> dict[str, Any]:
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
