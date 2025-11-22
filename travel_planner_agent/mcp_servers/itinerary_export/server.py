"""MCP server that lets agents save itineraries to shareable files."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import logging
import os
from pathlib import Path
import secrets
from typing import Any, AsyncIterator, Sequence
from urllib.parse import urlencode, urljoin

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExportConfig:
    """Configuration for the itinerary export server."""

    base_directory: Path
    public_url: str | None
    download_token: str | None

    @classmethod
    def from_env(cls) -> "ExportConfig":
        base = os.getenv("ITINERARY_EXPORT_DIR") or os.getenv("TRAVEL_EXPORT_DIR")
        directory = Path(base) if base else Path.cwd() / "exports"
        public_url = os.getenv("ITINERARY_EXPORT_PUBLIC_URL")
        token = os.getenv("ITINERARY_EXPORT_DOWNLOAD_TOKEN")
        return cls(
            base_directory=directory.expanduser().resolve(),
            public_url=public_url.rstrip("/") if public_url else None,
            download_token=token,
        )


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


def _sanitize_path_segment(segment: str) -> str:
    cleaned = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in segment.strip()
    )
    return cleaned or "segment"


def _clean_token(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum())


def _resolve_session_identifier(
    ctx: Context[ServerSession, LifespanState] | None, explicit: str | None
) -> str | None:
    if explicit:
        return explicit
    if ctx is None:
        return None

    for attr in ("session_id", "id"):
        candidate = getattr(ctx, attr, None)
        if candidate:
            return str(candidate)

    session = getattr(ctx, "session", None)
    if session is not None:
        for attr in ("session_id", "id"):
            candidate = getattr(session, attr, None)
            if candidate:
                return str(candidate)
    return None


def _normalize_identifier(requested: str | None, session_identifier: str | None) -> str:
    cleaned_requested = _clean_token(requested)
    if cleaned_requested:
        return cleaned_requested[:32]

    cleaned_session = _clean_token(session_identifier)[:12]
    random_fragment = secrets.token_hex(4)
    if cleaned_session:
        return f"{cleaned_session}-{random_fragment}"
    return random_fragment


def _resolve_export_path(base: Path, filename: str, subdirectory: str | None) -> Path:
    target_dir = base
    if subdirectory:
        sub_path = Path(subdirectory)
        parts: list[str] = []
        for part in sub_path.parts:
            if part in {"", "."}:
                continue
            if part == "..":
                raise ValueError("subdirectory may not contain '..'")
            parts.append(_sanitize_path_segment(part))
        if parts:
            target_dir = (base / Path(*parts)).resolve()
    target_path = (target_dir / filename).resolve()
    try:
        target_path.relative_to(base)
    except ValueError:
        raise ValueError("export path escapes base directory")
    return target_path


def _ensure_unique_path(path: Path) -> tuple[Path, int]:
    if not path.exists():
        return path, 0
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate, counter
        counter += 1


def _build_download_url(config: ExportConfig, relative_path: Path) -> str | None:
    public_url = os.getenv("ITINERARY_EXPORT_PUBLIC_URL") or config.public_url
    if not public_url:
        return None
    normalized = "/".join(relative_path.parts)
    cleaned_public_url = public_url.rstrip("/")
    url = urljoin(f"{cleaned_public_url}/", normalized)

    download_token = (
        os.getenv("ITINERARY_EXPORT_DOWNLOAD_TOKEN") or config.download_token
    )
    if download_token:
        query = urlencode({"token": download_token})
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"
    return url


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
    identifier: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Persist itinerary content as Markdown or plain text.

    Args:
        ctx: Optional MCP context for debug logging and session metadata.
        filename: Base name for the exported file (extension inferred from ``format``).
        content: Body to persist.
        format: ``"md"`` or ``"txt"``.
        subdirectory: Optional folder (relative to export root) to nest the file under.
        identifier: Optional stable identifier to embed in the filename; sanitized automatically.
        session_id: Optional session identifier to seed the generated identifier when ``identifier`` is not provided.

    Returns:
        Dictionary containing the saved file metadata including ``identifier`` and optional
        ``download_url`` (when ``ITINERARY_EXPORT_PUBLIC_URL`` is configured).
    """

    if not content:
        raise ValueError("content is required")
    if format not in {"md", "txt"}:
        raise ValueError("format must be 'md' or 'txt'")

    state = _require_state()
    session_identifier = _resolve_session_identifier(ctx, session_id)
    normalized_identifier = _normalize_identifier(identifier, session_identifier)
    base_label = filename.strip() or "trip-itinerary"
    composed_name = f"{base_label}-{normalized_identifier}"
    safe_name = _sanitize_filename(composed_name, format)
    file_path = _resolve_export_path(
        state.config.base_directory, safe_name, subdirectory
    )
    file_path, version = _ensure_unique_path(file_path)

    bytes_written = await asyncio.to_thread(_write_file, file_path, content)

    if ctx is not None:
        await ctx.debug("Wrote itinerary file %s", file_path)

    relative_path = file_path.relative_to(state.config.base_directory)
    download_url = _build_download_url(state.config, relative_path)

    response: dict[str, Any] = {
        "file_path": str(file_path),
        "format": format,
        "bytes_written": bytes_written,
        "identifier": normalized_identifier,
    }
    if download_url:
        response["download_url"] = download_url
    if version > 0:
        response["version"] = version
    return response


@mcp.tool()
async def save_itinerary_calendar(
    ctx: Context[ServerSession, LifespanState] | None = None,
    filename: str = "trip-calendar",
    events: Sequence[dict[str, str]] | None = None,
    subdirectory: str | None = None,
    identifier: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Generate a lightweight .ics file so travelers can import key events.

    Args mirror :func:`save_itinerary_file` with ``events`` providing calendar entries.

    Returns:
        Dictionary containing the generated calendar metadata including ``identifier``,
        byte size, and optional ``download_url``.
    """

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

    session_identifier = _resolve_session_identifier(ctx, session_id)
    normalized_identifier = _normalize_identifier(identifier, session_identifier)
    base_label = filename.strip() or "trip-calendar"
    composed_name = f"{base_label}-{normalized_identifier}"
    safe_name = _sanitize_filename(composed_name, "ics")
    file_path = _resolve_export_path(
        state.config.base_directory, safe_name, subdirectory
    )
    file_path, version = _ensure_unique_path(file_path)

    bytes_written = await asyncio.to_thread(_write_file, file_path, calendar_body)
    if ctx is not None:
        await ctx.debug("Wrote itinerary calendar %s", file_path)

    relative_path = file_path.relative_to(state.config.base_directory)
    download_url = _build_download_url(state.config, relative_path)

    response: dict[str, Any] = {
        "file_path": str(file_path),
        "format": "ics",
        "bytes_written": bytes_written,
        "event_count": len(events),
        "identifier": normalized_identifier,
    }
    if download_url:
        response["download_url"] = download_url
    if version > 0:
        response["version"] = version
    return response


def main() -> None:  # pragma: no cover - entry point
    logging.basicConfig(level=os.getenv("ITINERARY_EXPORT_LOG_LEVEL", "INFO"))
    mcp.run()


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
