from types import SimpleNamespace

from travel_planner_agent.mcp_servers.postgres_payments import server


def setup_function(_test_fn):
    server._FALLBACK_TOKENS.clear()


def test_resolve_session_identifier_prefers_explicit():
    assert server._resolve_session_identifier(None, " manual ") == "manual"


def test_resolve_session_identifier_generates_token_when_missing():
    ctx = SimpleNamespace(state=None)
    token = server._resolve_session_identifier(ctx, None)
    assert token.startswith("session-")


def test_resolve_user_identifier_reads_metadata_dict():
    ctx = SimpleNamespace(metadata={"user_id": " user42 "})
    assert server._resolve_user_identifier(ctx, None) == "user42"
