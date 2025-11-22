"""Serve itinerary exports over HTTP for local demos."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from .server import ExportConfig

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Itinerary Export Server", version="1.0.0")


class _ServerState:
    config: ExportConfig | None = None


def _load_config() -> ExportConfig:
    if _ServerState.config is None:
        config = ExportConfig.from_env()
        config.base_directory.mkdir(parents=True, exist_ok=True)
        _ServerState.config = config
        redacted = "***" if config.download_token else "<none>"
        LOGGER.info(
            "Serving itinerary exports from %s (public_url=%s, token=%s)",
            config.base_directory,
            config.public_url or "<unset>",
            redacted,
        )
    return _ServerState.config


async def _require_config() -> ExportConfig:
    return _load_config()


@app.get("/healthz")
async def health(_: ExportConfig = Depends(_require_config)) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _resolve_requested_path(config: ExportConfig, requested_path: str) -> Path:
    candidate = (config.base_directory / requested_path).resolve()
    try:
        candidate.relative_to(config.base_directory)
    except ValueError:
        raise HTTPException(status_code=404, detail="file not found")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return candidate


def _validate_token(config: ExportConfig, provided: str | None) -> None:
    expected = config.download_token
    if expected and provided != expected:
        raise HTTPException(status_code=403, detail="invalid or missing token")


@app.get("/exports/{requested_path:path}")
async def download_export(
    requested_path: str,
    request: Request,
    token: str | None = Query(default=None),
    config: ExportConfig = Depends(_require_config),
) -> FileResponse:
    provided = token or request.headers.get("X-Export-Token")
    _validate_token(config, provided)
    target = _resolve_requested_path(config, requested_path)
    return FileResponse(
        target,
        media_type="application/octet-stream",
        filename=target.name,
    )


def main() -> None:
    import uvicorn

    logging.basicConfig(level=os.getenv("ITINERARY_EXPORT_LOG_LEVEL", "INFO"))
    host = os.getenv("ITINERARY_EXPORT_HOST", "127.0.0.1")
    port = int(os.getenv("ITINERARY_EXPORT_PORT", "8765"))
    uvicorn.run(
        "travel_planner_agent.mcp_servers.itinerary_export.web_server:app",
        host=host,
        port=port,
        log_level=os.getenv("ITINERARY_EXPORT_SERVER_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
