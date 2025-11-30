from travel_planner_agent.tools import mcp, search


def test_search_flight_without_api_key(monkeypatch):
    monkeypatch.delenv("SERP_API_KEY", raising=False)
    result = search.search_flight(
        departure_id="SFO",
        arrival_id="LAX",
        outbound_date="2025-01-10",
        return_date="2025-01-15",
    )
    assert result["status"] == "error"


def test_collect_postgres_env_handles_missing_and_present(monkeypatch):
    monkeypatch.delenv("PAYMENTS_DB_URL", raising=False)
    assert mcp._collect_postgres_env() is None

    monkeypatch.setenv("PAYMENTS_DB_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("PAYMENTS_DB_POOL_MIN", "3")
    env = mcp._collect_postgres_env()
    assert env["PAYMENTS_DB_URL"].startswith("postgresql://")
    assert env["PAYMENTS_DB_POOL_MIN"] == "3"


def test_register_itinerary_toolset_produces_toolset():
    toolset = mcp._register_itinerary_export_toolset()
    assert toolset is not None
    assert isinstance(toolset, mcp.McpToolset)
