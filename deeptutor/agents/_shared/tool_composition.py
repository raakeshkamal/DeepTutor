"""Mastery-only per-turn tool composition policy.

The cleanup contract in ``docs-for-dev/cleanup-contract.md`` fixes the tool
surface for every turn: eleven mastery tools plus ``rag``, ``read_source``
and ``ask_user``. Composer toggles, context gates, partner whitelists and
capability-owned extras no longer add or subtract anything — a turn mounts
exactly :data:`MASTERY_TOOL_NAMES`.

The remaining helpers are compatibility shims for callers that still resolve
mount flags; none of them can widen the returned surface.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from deeptutor.modules.catalog import module_enabled
from deeptutor.tools.builtin import CONFIGURABLE_BUILTIN_TOOL_NAMES

#: The complete, ordered tool surface. Keep in lockstep with the contract.
MASTERY_TOOL_NAMES: tuple[str, ...] = (
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
)

AUTO_MOUNTED_TOOLS: frozenset[str] = frozenset(CONFIGURABLE_BUILTIN_TOOL_NAMES)

_CONDITIONAL_MOUNT_FLAGS: dict[str, str] = {
    "rag": "has_kb",
    "read_source": "has_sources",
}
_ALWAYS_ON_TOOLS: tuple[str, ...] = ("ask_user",)
_KB_COEXISTING_TOOLS: tuple[str, ...] = ("rag", "read_source")


@dataclass(frozen=True)
class ToolMountFlags:
    """Per-turn flags retained for callers; they cannot widen the surface."""

    has_kb: bool = False
    has_sources: bool = False
    has_book_authoring: bool = False
    has_memory: bool = False
    has_notebooks: bool = False
    has_question_bank: bool = False
    has_skills: bool = False
    has_deferred_tools: bool = False
    has_scientific_research: bool = False
    has_exec: bool = False
    has_mastery_nav: bool = False
    has_mastery_topics: bool = False


def compose_enabled_tools(
    *,
    registry: Any = None,
    requested_tools: list[str] | None = None,
    optional_whitelist: list[str] | None = None,
    mount_flags: ToolMountFlags | None = None,
    capability_owned: Iterable[str] = (),
    exclusive: bool = False,
    builtin_whitelist: set[str] | None = None,
    coexisting: Iterable[str] = (),
    forced: Iterable[str] = (),
    suppressed: Iterable[str] = (),
) -> list[str]:
    """Return the fixed mastery surface: exactly the 14 contracted tools.

    Every argument is accepted for caller compatibility, but none can change
    the result. This is the guard that keeps ``web_search``, ``web_fetch``,
    the workspace tools and all context-gated extras out of a turn.
    """
    return list(MASTERY_TOOL_NAMES)


def default_optional_tools(excluded: Iterable[str] = ()) -> list[str]:
    """No user-toggleable tools remain on this branch."""
    return []


def admin_enabled_optional_tools() -> list[str]:
    """No global toggles remain (partners and the settings screen are gone)."""
    return []


def _coexisting_mounts(declared: Iterable[str], **_: Any) -> list[str]:
    return []


def _finalize(
    names: Iterable[str],
    forced: Iterable[str] = (),
    suppressed: Iterable[str] = (),
) -> list[str]:
    dropped = {str(name) for name in suppressed}
    return [name for name in dict.fromkeys(names) if name not in dropped]


def _ordered_unique(names: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(names))


def user_has_memory() -> bool:
    try:
        if not module_enabled("memory"):
            return False
        from deeptutor.services.memory import get_memory_store

        store = get_memory_store()
        return any(
            store.read_raw("L3", slot).strip()
            for slot in ("recent", "profile", "scope", "preferences")
        )
    except Exception:
        return False


def user_has_notebooks() -> bool:
    try:
        if not module_enabled("notebook"):
            return False
        from deeptutor.services.notebook import get_notebook_manager

        notebooks = get_notebook_manager().list_notebooks()
        return isinstance(notebooks, list) and any(
            nb for nb in notebooks if str(nb.get("id") or "").strip()
        )
    except Exception:
        return False


def user_has_mastery_topics() -> bool:
    try:
        if not module_enabled("mastery"):
            return False
        from deeptutor.learning.navigation import learner_has_topics

        return learner_has_topics()
    except Exception:
        return False


def user_has_question_bank() -> bool:
    try:
        from deeptutor.services.session import get_sqlite_session_store

        return get_sqlite_session_store().has_question_bank_entries()
    except Exception:
        return False


def partner_can_record_questions() -> bool:
    """Partners no longer exist on this branch."""
    return False


__all__ = [
    "AUTO_MOUNTED_TOOLS",
    "MASTERY_TOOL_NAMES",
    "ToolMountFlags",
    "admin_enabled_optional_tools",
    "compose_enabled_tools",
    "default_optional_tools",
    "partner_can_record_questions",
    "user_has_mastery_topics",
    "user_has_memory",
    "user_has_notebooks",
    "user_has_question_bank",
]
