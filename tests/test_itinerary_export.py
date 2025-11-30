from travel_planner_agent.mcp_servers.itinerary_export import server


def test_compose_export_filename_uses_shared_identifier():
    identifier = "abc123"
    markdown_name = server._compose_export_filename(
        filename="trip-itinerary",
        identifier=identifier,
        extension="md",
    )
    calendar_name = server._compose_export_filename(
        filename="trip-itinerary",
        identifier=identifier,
        extension="ics",
    )

    assert markdown_name.rsplit(".", 1)[0] == calendar_name.rsplit(".", 1)[0]


def test_ensure_exports_prefix_appends_exports_segment():
    base = "http://localhost:8000"
    assert server._ensure_exports_prefix(base) == "http://localhost:8000/exports"
