"""Helpers for persisting lightweight session state across agent turns.

These utilities keep a structured summary of trip progress so agents can reuse
key facts without re-reading the entire transcript. The metadata is intentionally
compact and serializable so it can flow through ADK session storage.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import Agent as LlmAgent
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from google.adk.sessions.state import State

LOGGER = logging.getLogger(__name__)

_SESSION_ROOT_KEY = "trip_session"
_MAX_DIALOGUE_ENTRIES = 6
_MAX_EXPORT_RECORDS = 6
_MAX_BOOKING_RECORDS = 4


def register_session_callbacks(agent: LlmAgent) -> None:
    """Attach state-tracking callbacks to the given agent hierarchy."""

    agent.before_model_callback = _before_model_callback
    agent.after_model_callback = _after_model_callback
    agent.after_tool_callback = _after_tool_callback

    for child in getattr(agent, "sub_agents", []) or []:
        if isinstance(child, LlmAgent):
            register_session_callbacks(child)


def _before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest | Any,
    **_: Any,
) -> None:
    """Record the latest user utterance for this invocation."""

    try:
        ctx = callback_context
        content = ctx.user_content
        if content is None:
            return
        text = _content_to_text(content)
        if not text:
            return
        root = _ensure_trip_state(ctx.state)
        if root.get("last_user_invocation") == ctx.invocation_id:
            return
        root["last_user_invocation"] = ctx.invocation_id
        root["last_user_message"] = text
        _append_dialogue_entry(root, speaker="user", text=text)
        _update_trip_summary(ctx.state, root)
    except Exception as exc:  # defensive: never block the main flow
        LOGGER.debug("before_model_callback failed: %s", exc, exc_info=True)


def _after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse | Any,
    **_: Any,
) -> None:
    """Store concise agent replies and maintain a rolling dialogue."""

    try:
        ctx = callback_context
        response = llm_response
        content = getattr(response, "content", None)
        partial = getattr(response, "partial", None)
        if partial:
            return
        text = _content_to_text(content)
        if not text:
            return
        root = _ensure_trip_state(ctx.state)
        root["last_agent"] = ctx.agent_name
        root["last_agent_message"] = text
        _append_dialogue_entry(root, speaker=ctx.agent_name, text=text)
        _update_trip_summary(ctx.state, root)
    except Exception as exc:
        LOGGER.debug("after_model_callback failed: %s", exc, exc_info=True)


def _after_tool_callback(
    tool: BaseTool | Any,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: Any | None = None,
    **_: Any,
) -> None:
    """Capture structured results from function tools into session state."""

    try:
        root = _ensure_trip_state(tool_context.state)
        tool_name = _tool_name(tool)
        response = tool_response
        if tool_name == "search_flight":
            _record_flight_search(tool_context.state, root, args, response)
        elif tool_name == "search_hotel":
            _record_hotel_search(tool_context.state, root, args, response)
        elif tool_name == "simulate_flight_payment":
            _record_payment(tool_context.state, root, response, kind="flight")
        elif tool_name == "simulate_hotel_payment":
            _record_payment(tool_context.state, root, response, kind="hotel")
        elif tool_name == "cancel_payment":
            _record_cancellation(tool_context.state, root, response)
        elif tool_name == "save_itinerary_file":
            _record_export(tool_context.state, root, response, kind="itinerary")
        elif tool_name == "save_itinerary_calendar":
            _record_export(tool_context.state, root, response, kind="calendar")
        _update_trip_summary(tool_context.state, root)
    except Exception as exc:
        LOGGER.debug("after_tool_callback failed for %s: %s", tool, exc, exc_info=True)


def _ensure_trip_state(state: State) -> dict[str, Any]:
    trip = state.setdefault(
        _SESSION_ROOT_KEY,
        {
            "searches": {},
            "bookings": {},
            "exports": [],
            "recent_dialogue": [],
        },
    )
    trip.setdefault("searches", {})
    trip.setdefault("bookings", {})
    trip.setdefault("exports", [])
    trip.setdefault("recent_dialogue", [])
    trip["updated_at"] = _now()
    return trip


def _append_dialogue_entry(root: dict[str, Any], *, speaker: str, text: str) -> None:
    entry = {
        "speaker": speaker,
        "text": text.strip(),
        "timestamp": _now(),
    }
    dialogue: list[dict[str, Any]] = root.setdefault("recent_dialogue", [])
    dialogue.append(entry)
    if len(dialogue) > _MAX_DIALOGUE_ENTRIES:
        del dialogue[: len(dialogue) - _MAX_DIALOGUE_ENTRIES]


def _record_flight_search(
    state: State,
    root: dict[str, Any],
    args: dict[str, Any],
    response: Any,
) -> None:
    if not isinstance(response, dict):
        return
    searches = root.setdefault("searches", {})
    params = {
        "departure_id": args.get("departure_id"),
        "arrival_id": args.get("arrival_id"),
        "outbound_date": args.get("outbound_date"),
        "return_date": args.get("return_date"),
        "currency": args.get("currency") or response.get("currency"),
    }
    flights = response.get("best_flights") or []
    summaries = [_trim_flight_info(item) for item in flights[:2]]
    searches["flight"] = {
        "params": {k: v for k, v in params.items() if v},
        "top_results": summaries,
        "other_results_count": max(0, len(response.get("other_flights") or [])),
        "return_queries_executed": response.get("return_queries_executed"),
        "fetched_at": _now(),
    }
    if params.get("departure_id"):
        state["origin"] = params["departure_id"]
    if params.get("arrival_id"):
        state["destination"] = params["arrival_id"]
    if params.get("outbound_date"):
        state["start_date"] = params["outbound_date"]
    if params.get("return_date"):
        state["end_date"] = params["return_date"]
    if params.get("currency"):
        state["currency"] = params["currency"].upper()


def _record_hotel_search(
    state: State,
    root: dict[str, Any],
    args: dict[str, Any],
    response: Any,
) -> None:
    if not isinstance(response, dict):
        return
    searches = root.setdefault("searches", {})
    params = {
        "location": args.get("location"),
        "check_in_date": args.get("check_in_date"),
        "check_out_date": args.get("check_out_date"),
        "adults": args.get("adults"),
        "children": args.get("children"),
        "currency": args.get("currency"),
    }
    properties = response.get("properties") or []
    summaries = [_trim_hotel_info(item) for item in properties[:3]]
    searches["hotel"] = {
        "params": {k: v for k, v in params.items() if v},
        "top_results": summaries,
        "fetched_at": _now(),
    }
    if params.get("location"):
        state["destination"] = params["location"]
    if params.get("check_in_date"):
        state["start_date"] = params["check_in_date"]
    if params.get("check_out_date"):
        state["end_date"] = params["check_out_date"]
    if params.get("currency"):
        state["currency"] = params["currency"].upper()


def _record_payment(
    state: State,
    root: dict[str, Any],
    response: Any,
    *,
    kind: str,
) -> None:
    if not isinstance(response, dict):
        return
    transaction = response.get("payment_transaction") or {}
    request = response.get("payment_request") or {}
    confirmation = transaction.get("confirmation_code")
    if not confirmation:
        return
    record = {
        "confirmation_code": confirmation,
        "vendor_reference": transaction.get("vendor_reference"),
        "amount_cents": request.get("amount_cents"),
        "currency": request.get("currency"),
        "status": transaction.get("status"),
        "created_at": transaction.get("created_at"),
        "metadata": transaction.get("metadata"),
    }
    bookings = root.setdefault("bookings", {})
    bucket = bookings.setdefault(f"{kind}s", [])
    bucket[:] = [
        entry for entry in bucket if entry.get("confirmation_code") != confirmation
    ]
    bucket.insert(0, record)
    del bucket[_MAX_BOOKING_RECORDS:]
    if kind == "flight":
        state["flight_confirmation_code"] = confirmation
        state["flight_pnr"] = transaction.get("vendor_reference")
    elif kind == "hotel":
        state["hotel_confirmation_code"] = confirmation
    state["payment_currency"] = request.get("currency") or state.get("currency")


def _record_cancellation(state: State, root: dict[str, Any], response: Any) -> None:
    if not isinstance(response, dict):
        return
    transaction = response.get("payment_transaction") or {}
    confirmation = transaction.get("confirmation_code")
    if not confirmation:
        return
    bookings = root.setdefault("bookings", {})
    for key in ("flights", "hotels"):
        bucket = bookings.get(key)
        if not bucket:
            continue
        for entry in bucket:
            if entry.get("confirmation_code") == confirmation:
                status = transaction.get("status")
                entry.update(
                    {
                        "status": status,
                        "metadata": transaction.get("metadata"),
                    }
                )
                if status == "cancelled":
                    if (
                        key == "flights"
                        and state.get("flight_confirmation_code") == confirmation
                    ):
                        state["flight_confirmation_code"] = ""
                        state["flight_pnr"] = ""
                    if (
                        key == "hotels"
                        and state.get("hotel_confirmation_code") == confirmation
                    ):
                        state["hotel_confirmation_code"] = ""
                break


def _record_export(
    state: State,
    root: dict[str, Any],
    response: Any,
    *,
    kind: str,
) -> None:
    if not isinstance(response, dict):
        return
    record = {
        "type": kind,
        "file_path": response.get("file_path"),
        "format": response.get("format"),
        "bytes_written": response.get("bytes_written"),
        "identifier": response.get("identifier"),
        "download_url": response.get("download_url"),
        "version": response.get("version"),
        "saved_at": _now(),
    }
    exports = root.setdefault("exports", [])
    exports.insert(0, record)
    del exports[_MAX_EXPORT_RECORDS:]
    state["latest_export_identifier"] = record.get("identifier")
    if record.get("download_url"):
        state[f"latest_{kind}_download_url"] = record["download_url"]


def _trim_flight_info(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    keep_keys = {
        "airline",
        "flight_number",
        "price",
        "duration",
        "departure_airport",
        "arrival_airport",
        "layovers",
    }
    return {key: item.get(key) for key in keep_keys if key in item}


def _trim_hotel_info(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    keep_keys = {
        "name",
        "rate_per_night",
        "total_price",
        "overall_rating",
        "reviews",
        "link",
    }
    return {key: item.get(key) for key in keep_keys if key in item}


def _update_trip_summary(state: State, root: dict[str, Any]) -> None:
    origin = state.get("origin")
    destination = state.get("destination")
    start = state.get("start_date")
    end = state.get("end_date")
    currency = state.get("currency")

    segments: list[str] = []
    if origin and destination:
        segments.append(f"Route: {origin} → {destination}")
    elif destination:
        segments.append(f"Destination: {destination}")
    if start and end:
        segments.append(f"Dates: {start} to {end}")
    elif start:
        segments.append(f"Start: {start}")

    flight_top = (root.get("searches", {}).get("flight", {}) or {}).get("top_results")
    if flight_top:
        price = flight_top[0].get("price")
        airline = flight_top[0].get("airline")
        if airline or price:
            segments.append(
                "Flight: "
                + ", ".join(filter(None, [airline, str(price) if price else None]))
            )

    hotel_top = (root.get("searches", {}).get("hotel", {}) or {}).get("top_results")
    if hotel_top:
        name = hotel_top[0].get("name")
        rate = hotel_top[0].get("rate_per_night")
        if name or rate:
            segments.append(
                "Hotel: " + ", ".join(filter(None, [name, str(rate) if rate else None]))
            )

    latest_exports = root.get("exports") or []
    if latest_exports:
        export = latest_exports[0]
        if export.get("download_url"):
            segments.append(f"Download: {export['download_url']}")
        elif export.get("file_path"):
            segments.append(f"Saved: {export['file_path']}")

    if currency:
        segments.append(f"Currency: {currency}")

    summary = " | ".join(segments)
    if summary:
        state["trip_summary"] = summary[:600]


def _tool_name(tool: BaseTool | Any) -> str:
    if isinstance(tool, BaseTool) and getattr(tool, "name", None):
        return tool.name
    if hasattr(tool, "__name__"):
        return tool.__name__
    return tool.__class__.__name__


def _content_to_text(content: types.Content | None) -> str:
    if not content or not getattr(content, "parts", None):
        return ""
    pieces: list[str] = []
    for part in content.parts:  # type: ignore[attr-defined]
        text = getattr(part, "text", None)
        if text and not getattr(part, "thought", False):
            pieces.append(text)
    return " ".join(piece.strip() for piece in pieces if piece.strip())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
