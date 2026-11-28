"""Contract guard: a turn mounts exactly the 14 mastery tools, never a web tool.

See ``docs-for-dev/cleanup-contract.md``. This test is deliberately free of
I/O and settings so it fails loudly the moment a composer toggle, a context
gate, a capability-owned extra or a partner ``forced`` tool is allowed to
widen the surface again.
"""

from deeptutor.agents._shared.tool_composition import (
    MASTERY_TOOL_NAMES,
    compose_enabled_tools,
)

EXPECTED_TOOLS = frozenset(
    {
        "mastery_prepare_lesson",
        "mastery_status",
        "mastery_quiz",
        "mastery_assess",
        "mastery_grade",
        "mastery_note_explained",
        "mastery_skip_question",
        "mastery_mode",
        "mastery_profile",
        "mastery_defer_objective",
        "mastery_repair_question",
        "rag",
        "read_source",
        "ask_user",
    }
)


def test_mastery_surface_matches_the_contract() -> None:
    assert len(MASTERY_TOOL_NAMES) == 14
    assert set(MASTERY_TOOL_NAMES) == EXPECTED_TOOLS
    assert len(set(MASTERY_TOOL_NAMES)) == 14


def test_no_other_tool_can_be_mounted_on_a_mastery_turn() -> None:
    mounted = compose_enabled_tools(
        registry=object(),
        requested_tools=["web_search", "web_fetch", "brainstorm"],
        optional_whitelist=["web_search", "brainstorm"],
        mount_flags=None,
        capability_owned=["workspace_present", "exec", "read_memory"],
        exclusive=False,
        forced=["partner_read"],
        suppressed=[],
    )
    assert mounted == list(MASTERY_TOOL_NAMES)
    for forbidden in ("web_search", "web_fetch", "exec", "workspace_present", "partner_read"):
        assert forbidden not in mounted


def test_ask_user_is_the_only_always_on_tool() -> None:
    from deeptutor.agents._shared import tool_composition

    assert tool_composition._ALWAYS_ON_TOOLS == ("ask_user",)
    assert set(tool_composition._CONDITIONAL_MOUNT_FLAGS) == {"rag", "read_source"}
    assert not hasattr(tool_composition, "WORKSPACE_BASELINE_TOOLS")
