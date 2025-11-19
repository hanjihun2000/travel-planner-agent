"""Postgres-backed MCP server for booking payment simulations.

This server exposes lightweight tools that allow agents to validate database
connectivity before running payment simulations. Future iterations can extend the
same server with additional tools (for example, `simulate_payment`).

Run locally:

```
python -m venv .venv
source .venv/bin/activate
pip install psycopg[binary,pool] mcp
export PAYMENTS_DB_URL="postgresql://user:password@localhost:5432/travel_payments"
python -m travel_planner_agent.mcp_servers.postgres_payments.server
```
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
import secrets
from typing import Any, AsyncIterator

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from psycopg.types.json import Json

from .config import PostgresConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LifespanState:
    """Holds application resources available during MCP requests."""

    pool: AsyncConnectionPool
    config: PostgresConfig


async def _ensure_schema(pool: AsyncConnectionPool) -> None:
    """Create the minimal schema required for payment simulations."""

    async with pool.connection() as conn:
        await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            await cur.execute("SET application_name = 'travel_planner_payments_mcp';")
            await cur.execute("SET TIME ZONE 'UTC';")
            await cur.execute(
                """
            CREATE TABLE IF NOT EXISTS payment_requests (
                id BIGSERIAL PRIMARY KEY,
                vendor TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency TEXT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
            )
            await cur.execute(
                """
            ALTER TABLE payment_requests
            ADD COLUMN IF NOT EXISTS session_id TEXT,
            ADD COLUMN IF NOT EXISTS user_id TEXT;
            """
            )
            await cur.execute(
                """
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id BIGSERIAL PRIMARY KEY,
                request_id BIGINT NOT NULL REFERENCES payment_requests(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                confirmation_code TEXT NOT NULL,
                vendor_reference TEXT,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
            )
            await cur.execute(
                """
            ALTER TABLE payment_transactions
            ADD COLUMN IF NOT EXISTS session_id TEXT,
            ADD COLUMN IF NOT EXISTS user_id TEXT;
            """
            )


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[LifespanState]:
    """Open shared resources (Postgres pool) for the MCP server lifecycle."""

    config = PostgresConfig.from_env()
    logger.info(
        "Opening Postgres connection pool (min=%s, max=%s)",
        config.pool_min_size,
        config.pool_max_size,
    )

    pool = AsyncConnectionPool(
        config.database_url,
        min_size=config.pool_min_size,
        max_size=config.pool_max_size,
        kwargs={"options": f"-c statement_timeout={config.statement_timeout_ms}"},
        open=False,
    )
    await pool.open()
    state = LifespanState(pool=pool, config=config)
    _set_lifespan_state(state)
    try:
        await _ensure_schema(pool)
        yield state
    finally:
        logger.info("Closing Postgres connection pool")
        await pool.close()
        _set_lifespan_state(None)


mcp = FastMCP(
    name="payments-postgres",
    instructions="Postgres-backed payment utility tools for the travel planner agent.",
    lifespan=lifespan,
)


_STATE: LifespanState | None = None


def _set_lifespan_state(state: LifespanState | None) -> None:
    global _STATE
    _STATE = state


def _require_state() -> LifespanState:
    if _STATE is None:
        logger.error("Lifespan state is not available")
        raise RuntimeError("lifespan state unavailable")
    return _STATE


def _jsonb(value: Any) -> Json:
    """Wrap Python values for JSONB storage."""

    return Json(value)


@mcp.tool()
async def ping_database(
    ctx: Context[ServerSession, LifespanState] | None = None,
) -> dict[str, str | int | float]:
    """Run a lightweight connectivity check against the Postgres database."""

    state = _require_state()

    try:
        async with state.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                row = await cur.fetchone()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("ping_database failed: %s", exc)
        if ctx is not None:
            await ctx.debug(f"Postgres ping failed: {exc}")
        raise

    status = "ok" if row and row[0] == 1 else "unexpected result"

    payload = {
        "status": status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "pool_min_size": state.config.pool_min_size,
        "pool_max_size": state.config.pool_max_size,
    }

    logger.debug("ping_database returning %s", payload)
    if ctx is not None:
        await ctx.debug("Pinged Postgres database")
    return payload


@mcp.tool()
async def list_payment_activity(
    ctx: Context[ServerSession, LifespanState] | None = None,
    limit: int = 20,
) -> dict[str, list[dict[str, Any]]]:
    """Return recent simulated payment requests and transactions."""

    if limit <= 0:
        raise ValueError("limit must be positive")

    state = _require_state()
    query = """
        SELECT
            pr.id AS request_id,
            pr.session_id AS request_session_id,
            pr.user_id AS request_user_id,
            pr.vendor,
            pr.amount_cents,
            pr.currency,
            pr.metadata AS request_metadata,
            pr.created_at AS request_created_at,
            pt.id AS transaction_id,
            pt.session_id AS transaction_session_id,
            pt.user_id AS transaction_user_id,
            pt.status,
            pt.confirmation_code,
            pt.vendor_reference,
            pt.metadata AS transaction_metadata,
            pt.created_at AS transaction_created_at
        FROM payment_requests pr
        LEFT JOIN payment_transactions pt ON pt.request_id = pr.id
        ORDER BY pr.created_at DESC, COALESCE(pt.created_at, pr.created_at) DESC
        LIMIT %s
        """

    try:
        async with state.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (limit,))
                rows = await cur.fetchall()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("list_payment_activity failed: %s", exc)
        if ctx is not None:
            await ctx.debug(f"Failed to list payment activity: {exc}")
        raise

    payload = [dict(row) for row in rows]

    if ctx is not None:
        await ctx.debug("Retrieved %s payment activity rows", len(payload))
    return {"payments": payload}


@mcp.tool()
async def simulate_hotel_payment(
    ctx: Context[ServerSession, LifespanState] | None = None,
    hotel_name: str = "",
    amount_cents: int = 0,
    currency: str = "USD",
    session_id: str | None = None,
    user_id: str | None = None,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    guest_name: str | None = None,
) -> dict[str, Any]:
    """Simulate a hotel booking payment transaction.

    Args:
        ctx: Optional MCP context for debug logging.
        hotel_name: Name of the hotel vendor.
        amount_cents: Payment amount in cents (must be positive).
        currency: Three-letter currency code (default "USD").
        session_id: Optional session identifier for tracking.
        user_id: Optional user identifier for tracking.
        check_in_date: Check-in date in ISO format (e.g., "2025-12-01").
        check_out_date: Check-out date in ISO format (e.g., "2025-12-05").
        guest_name: Name of the primary guest.

    Returns:
        Dictionary containing the created payment request and transaction details,
        including the simulated confirmation code.
    """
    if not hotel_name or not hotel_name.strip():
        raise ValueError("hotel_name is required")
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if not currency or len(currency) != 3:
        raise ValueError("currency must be a 3-letter code")

    state = _require_state()

    metadata = {
        "booking_type": "hotel",
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "guest_name": guest_name,
    }

    # Generate simulated confirmation code

    confirmation_code = f"HTL-{secrets.token_hex(4).upper()}"

    try:
        async with state.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # Insert payment request
                await cur.execute(
                    """
                    INSERT INTO payment_requests
                        (vendor, amount_cents, currency, session_id, user_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, vendor, amount_cents, currency, session_id, user_id, metadata, created_at
                    """,
                    (
                        hotel_name,
                        amount_cents,
                        currency,
                        session_id,
                        user_id,
                        _jsonb(metadata),
                    ),
                )
                request_row = await cur.fetchone()
                if not request_row:
                    raise RuntimeError("Failed to create payment request")

                request_id = request_row["id"]

                # Insert payment transaction
                await cur.execute(
                    """
                    INSERT INTO payment_transactions
                        (request_id, status, confirmation_code, vendor_reference, session_id, user_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, request_id, status, confirmation_code, vendor_reference, session_id, user_id, metadata, created_at
                    """,
                    (
                        request_id,
                        "confirmed",
                        confirmation_code,
                        f"VENDOR-{secrets.token_hex(3).upper()}",
                        session_id,
                        user_id,
                        _jsonb({"payment_method": "simulated_credit_card"}),
                    ),
                )
                transaction_row = await cur.fetchone()
                if not transaction_row:
                    raise RuntimeError("Failed to create payment transaction")

    except Exception as exc:
        logger.exception("simulate_hotel_payment failed: %s", exc)
        if ctx is not None:
            await ctx.debug(f"Hotel payment simulation failed: {exc}")
        raise

    result = {
        "payment_request": dict(request_row),
        "payment_transaction": dict(transaction_row),
    }

    if ctx is not None:
        await ctx.debug(f"Simulated hotel payment: {confirmation_code}")

    return result


@mcp.tool()
async def simulate_flight_payment(
    ctx: Context[ServerSession, LifespanState] | None = None,
    airline: str = "",
    amount_cents: int = 0,
    currency: str = "USD",
    session_id: str | None = None,
    user_id: str | None = None,
    departure_airport: str | None = None,
    arrival_airport: str | None = None,
    departure_date: str | None = None,
    passenger_name: str | None = None,
) -> dict[str, Any]:
    """Simulate a flight booking payment transaction.

    Args:
        ctx: Optional MCP context for debug logging.
        airline: Name of the airline vendor.
        amount_cents: Payment amount in cents (must be positive).
        currency: Three-letter currency code (default "USD").
        session_id: Optional session identifier for tracking.
        user_id: Optional user identifier for tracking.
        departure_airport: IATA code for departure airport (e.g., "SFO").
        arrival_airport: IATA code for arrival airport (e.g., "LHR").
        departure_date: Departure date in ISO format (e.g., "2025-12-01").
        passenger_name: Name of the primary passenger.

    Returns:
        Dictionary containing the created payment request and transaction details,
        including the simulated PNR/confirmation code.
    """
    if not airline or not airline.strip():
        raise ValueError("airline is required")
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if not currency or len(currency) != 3:
        raise ValueError("currency must be a 3-letter code")

    state = _require_state()

    metadata = {
        "booking_type": "flight",
        "departure_airport": departure_airport,
        "arrival_airport": arrival_airport,
        "departure_date": departure_date,
        "passenger_name": passenger_name,
    }

    # Generate simulated PNR/confirmation code

    confirmation_code = f"FLT-{secrets.token_hex(3).upper()}"
    pnr = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))

    try:
        async with state.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # Insert payment request
                await cur.execute(
                    """
                    INSERT INTO payment_requests
                        (vendor, amount_cents, currency, session_id, user_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, vendor, amount_cents, currency, session_id, user_id, metadata, created_at
                    """,
                    (
                        airline,
                        amount_cents,
                        currency,
                        session_id,
                        user_id,
                        _jsonb(metadata),
                    ),
                )
                request_row = await cur.fetchone()
                if not request_row:
                    raise RuntimeError("Failed to create payment request")

                request_id = request_row["id"]

                # Insert payment transaction with PNR
                await cur.execute(
                    """
                    INSERT INTO payment_transactions
                        (request_id, status, confirmation_code, vendor_reference, session_id, user_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, request_id, status, confirmation_code, vendor_reference, session_id, user_id, metadata, created_at
                    """,
                    (
                        request_id,
                        "confirmed",
                        confirmation_code,
                        pnr,
                        session_id,
                        user_id,
                        _jsonb({"payment_method": "simulated_credit_card", "pnr": pnr}),
                    ),
                )
                transaction_row = await cur.fetchone()
                if not transaction_row:
                    raise RuntimeError("Failed to create payment transaction")

    except Exception as exc:
        logger.exception("simulate_flight_payment failed: %s", exc)
        if ctx is not None:
            await ctx.debug(f"Flight payment simulation failed: {exc}")
        raise

    result = {
        "payment_request": dict(request_row),
        "payment_transaction": dict(transaction_row),
    }

    if ctx is not None:
        await ctx.debug(f"Simulated flight payment: {confirmation_code} (PNR: {pnr})")

    return result


@mcp.tool()
async def cancel_payment(
    ctx: Context[ServerSession, LifespanState] | None = None,
    confirmation_code: str = "",
    reason: str | None = None,
) -> dict[str, Any]:
    """Cancel or refund a payment transaction by confirmation code.

    Args:
        ctx: Optional MCP context for debug logging.
        confirmation_code: The confirmation code from the original transaction.
        reason: Optional cancellation reason.

    Returns:
        Dictionary containing the updated transaction details with status
        changed to "cancelled".
    """
    if not confirmation_code or not confirmation_code.strip():
        raise ValueError("confirmation_code is required")

    state = _require_state()

    try:
        async with state.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # Find and update the transaction
                await cur.execute(
                    """
                    UPDATE payment_transactions
                    SET status = 'cancelled',
                        metadata = metadata || %s::jsonb
                    WHERE confirmation_code = %s
                    RETURNING id, request_id, status, confirmation_code, vendor_reference, 
                              session_id, user_id, metadata, created_at
                    """,
                    (
                        _jsonb(
                            {
                                "cancellation_reason": reason,
                                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ),
                        confirmation_code,
                    ),
                )
                transaction_row = await cur.fetchone()

                if not transaction_row:
                    raise ValueError(
                        f"No transaction found with confirmation code: {confirmation_code}"
                    )

    except ValueError:
        raise
    except Exception as exc:
        logger.exception("cancel_payment failed: %s", exc)
        if ctx is not None:
            await ctx.debug(f"Payment cancellation failed: {exc}")
        raise

    result = {"payment_transaction": dict(transaction_row)}

    if ctx is not None:
        await ctx.debug(f"Cancelled payment: {confirmation_code}")

    return result


def main() -> None:
    """Entry point for running the MCP server via stdio."""

    logging.basicConfig(
        level=os.getenv("PAYMENTS_MCP_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    mcp.run()


if __name__ == "__main__":
    main()
