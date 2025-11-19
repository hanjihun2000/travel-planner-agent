"""MCP server that lets agents save itineraries to shareable files."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Sequence

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExportConfig:
    """Configuration for the itinerary export server."""

    base_directory: Path

    @classmethod
    def from_env(cls) -> "ExportConfig":
        base = os.getenv("ITINERARY_EXPORT_DIR") or os.getenv("TRAVEL_EXPORT_DIR")
        directory = Path(base) if base else Path.cwd() / "exports"
        return cls(base_directory=directory.expanduser().resolve())


@dataclass(slots=True)
class LifespanState:
    config: ExportConfig


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[LifespanState]:
    config = ExportConfig.from_env()
    config.base_directory.mkdir(parents=True, exist_ok=True)
    logger.info("Itinerary exports will be stored under %s", config.base_directory)
    state = LifespanState(config=config)
    _set_state(state)
    try:
        yield state
    finally:
        _set_state(None)


mcp = FastMCP(
    name="itinerary-export",
    instructions="Utilities for saving itineraries to markdown or calendar files.",
    lifespan=lifespan,
)


_STATE: LifespanState | None = None


def _set_state(state: LifespanState | None) -> None:
    global _STATE
    _STATE = state


def _require_state() -> LifespanState:
    if _STATE is None:  # pragma: no cover - defensive programming
        raise RuntimeError("itinerary export server not initialized")
    return _STATE


def _sanitize_filename(name: str, extension: str) -> str:
    safe = (
        "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in name.strip())
        or "itinerary"
    )
    if not safe.lower().endswith(f".{extension}"):
        safe = f"{safe}.{extension}"
    return safe


def _format_ics_datetime(value: str) -> str:
    dt = datetime.fromisoformat(value)
    return dt.strftime("%Y%m%dT%H%M%S")


def _write_file(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


@mcp.tool()
async def save_itinerary_file(
    ctx: Context[ServerSession, LifespanState] | None = None,
    filename: str = "trip-itinerary",
    content: str = "",
    format: str = "md",
    subdirectory: str | None = None,
) -> dict[str, Any]:
    """Persist itinerary content as Markdown or plain text."""

    if not content:
        raise ValueError("content is required")
    if format not in {"md", "txt"}:
        raise ValueError("format must be 'md' or 'txt'")

    state = _require_state()
    safe_name = _sanitize_filename(filename, format)
    directory = state.config.base_directory
    if subdirectory:
        directory = directory / Path(subdirectory)
    file_path = directory / safe_name

    bytes_written = await asyncio.to_thread(_write_file, file_path, content)

    if ctx is not None:
        await ctx.debug("Wrote itinerary file %s", file_path)

    return {
        "file_path": str(file_path),
        "format": format,
        "bytes_written": bytes_written,
    }


@mcp.tool()
async def save_itinerary_calendar(
    ctx: Context[ServerSession, LifespanState] | None = None,
    filename: str = "trip-calendar",
    events: Sequence[dict[str, str]] | None = None,
    subdirectory: str | None = None,
) -> dict[str, Any]:
    """Generate a lightweight .ics file so travelers can import key events."""

    if not events:
        raise ValueError("events must include at least one entry")

    state = _require_state()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//travel-planner-agent//EN",
    ]
    for item in events:
        start = item.get("start")
        end = item.get("end")
        summary = item.get("summary") or "Itinerary Event"
        description = item.get("description") or ""
        location = item.get("location") or ""
        if not (start and end):
            raise ValueError("each event requires 'start' and 'end' ISO timestamps")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                f"LOCATION:{location}",
                f"DTSTART:{_format_ics_datetime(start)}",
                f"DTEND:{_format_ics_datetime(end)}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    calendar_body = "\n".join(lines)

    safe_name = _sanitize_filename(filename, "ics")
    directory = state.config.base_directory
    if subdirectory:
        directory = directory / Path(subdirectory)
    file_path = directory / safe_name

    bytes_written = await asyncio.to_thread(_write_file, file_path, calendar_body)
    if ctx is not None:
        await ctx.debug("Wrote itinerary calendar %s", file_path)

    return {
        "file_path": str(file_path),
        "format": "ics",
        "bytes_written": bytes_written,
        "event_count": len(events),
    }


def main() -> None:  # pragma: no cover - entry point
    logging.basicConfig(level=os.getenv("ITINERARY_EXPORT_LOG_LEVEL", "INFO"))
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
