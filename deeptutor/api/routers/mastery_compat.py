"""Mastery-only compatibility shims for the retained workspace shell.

The cleanup removed partners, reading, subagents, MCP, the task board, the
learning dashboard and the settings-driven tool catalogue. A handful of shared
shell components (sidebar, composer, viewer providers) still probe those read
endpoints on mount even on the mastery page. Rather than restore those features,
serve bounded empty payloads so the shell stays quiet and deterministic. None
of these routes expose a capability, a tool or a credential.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/dashboard/learning-index")
async def learning_index() -> dict:
    # useLearningIndex calls payload.failed.includes(kind) for every kind.
    return {
        "sources": {
            "books": [],
            "mastery": [],
            "reading": [],
            "watching": [],
            "practice": [],
        },
        "failed": [],
    }


@router.get("/api/partners")
async def partners() -> list:
    return []


@router.get("/api/partners/navigation")
async def partner_navigation() -> dict:
    return {"partners": [], "groups": [], "agents": []}


@router.get("/api/partner-groups")
async def partner_groups() -> list:
    return []


@router.get("/api/reading/workspaces/index")
async def reading_workspaces() -> list:
    return []


@router.get("/api/settings/workspace/registrations")
async def workspace_registrations() -> list:
    return []


@router.get("/api/settings/workspace/resources")
async def workspace_resources() -> dict:
    return {}


@router.get("/api/space/mcp/servers")
async def space_mcp_servers() -> dict:
    return {"servers": {}}


@router.get("/api/subagents/settings")
async def subagent_settings() -> dict:
    return {}


@router.get("/api/tools")
async def tool_settings() -> dict:
    # No user-toggleable tools remain on this branch.
    return {"enabled_optional_tools": []}
