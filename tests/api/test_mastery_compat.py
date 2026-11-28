"""The mastery-only shell shims never restore a deleted feature."""

from __future__ import annotations

import asyncio

from deeptutor.api.routers.mastery_compat import router


def test_only_read_endpoints_exist() -> None:
    methods = {method for route in router.routes for method in getattr(route, "methods", set())}
    assert methods <= {"GET"}


def test_learning_index_has_the_shape_the_sidebar_reads() -> None:
    payload = asyncio.run(
        next(r.endpoint for r in router.routes if r.path == "/api/dashboard/learning-index")()
    )
    assert payload["failed"] == []
    assert all(rows == [] for rows in payload["sources"].values())


def test_tool_toggles_are_empty() -> None:
    payload = asyncio.run(
        next(r.endpoint for r in router.routes if r.path == "/api/tools")()
    )
    assert payload == {"enabled_optional_tools": []}
