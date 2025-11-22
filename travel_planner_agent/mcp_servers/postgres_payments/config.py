"""Configuration helpers for the Postgres payments MCP server."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class PostgresConfig:
    """Holds connection settings for the Postgres payments MCP server."""

    database_url: str
    pool_min_size: int = 1
    pool_max_size: int = 5
    statement_timeout_ms: int = 60000

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        """Create configuration from environment variables.

        Expected variables:
            PAYMENTS_DB_URL: PostgreSQL DSN, e.g. ``postgresql://user:pass@localhost:5432/travel_payments``.
            PAYMENTS_DB_POOL_MIN: Optional minimum connections for the pool (default: 1).
            PAYMENTS_DB_POOL_MAX: Optional maximum connections for the pool (default: 5).
            PAYMENTS_DB_STATEMENT_TIMEOUT_MS: Optional statement timeout in milliseconds (default: 60000).
        """

        url = os.getenv("PAYMENTS_DB_URL")
        if not url:
            raise RuntimeError(
                "PAYMENTS_DB_URL must be set to connect the Postgres MCP server."
            )

        pool_min = int(os.getenv("PAYMENTS_DB_POOL_MIN", "1"))
        pool_max = int(os.getenv("PAYMENTS_DB_POOL_MAX", "5"))
        if pool_max < pool_min:
            raise ValueError("PAYMENTS_DB_POOL_MAX must be >= PAYMENTS_DB_POOL_MIN")

        timeout = int(os.getenv("PAYMENTS_DB_STATEMENT_TIMEOUT_MS", "60000"))

        return cls(
            database_url=url,
            pool_min_size=pool_min,
            pool_max_size=pool_max,
            statement_timeout_ms=timeout,
        )
