"""Expose a mastery topic's selected materials to the tutoring turn.

Mastery-only cleanup: the single supported material is a knowledge base.
Books, notebooks, co-writer pages, question banks and partner-group
transcripts no longer exist, so no lazy imports into those packages remain
here. A knowledge base (and a file picked out of one) is searched with
``rag``; nothing is expanded into ``source_index`` — the tutor decides,
knowledge point by knowledge point, whether to query it this turn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Ceilings retained for callers that still import them; nothing on this
# branch produces readable chapter-sized materials any more.
MAX_CHAPTER_CHARS = 24_000
MAX_BOOK_CHARS = 240_000
MAX_NOTEBOOK_CHARS = 120_000
MAX_TOTAL_CHARS = 600_000
MAX_CHAPTERS_PER_BOOK = 40
MAX_OUTLINE_CHARS = 220


@dataclass(frozen=True)
class TopicMaterial:
    """One row of the topic-materials manifest.

    ``sid`` is empty for materials that are searched rather than read (a
    knowledge base), and for materials that could not be loaded. Only rows
    with a ``sid`` reach ``source_index``.
    """

    sid: str
    kind: str
    name: str
    outline: str = ""
    full_text: str = ""
    available: bool = True
    note: str = ""

    @property
    def readable(self) -> bool:
        return bool(self.sid and self.full_text.strip())


@dataclass
class TopicMaterials:
    materials: list[TopicMaterial] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.materials

    def source_index(self) -> dict[str, str]:
        return {m.sid: m.full_text for m in self.materials if m.readable}


def _clip(text: str, limit: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "…"


def _format_size(char_count: int) -> str:
    if char_count >= 1024:
        return f"~{round(char_count / 1024)} KB"
    return f"~{char_count} chars"


def _clean_name(value: str) -> str:
    return " ".join(str(value or "").split())


def build_topic_materials(sources: Iterable[Any]) -> TopicMaterials:
    """Resolve a topic's persisted sources into searchable rows.

    Synchronous storage I/O — call it off the event loop. One unloadable
    source degrades to an ``unavailable`` row and never takes the turn down
    with it: tutoring that silently loses a material is worse than tutoring
    that says so.
    """
    result = TopicMaterials()
    for source in sorted(sources, key=lambda item: getattr(item, "position", 0)):
        kind = getattr(getattr(source, "kind", None), "value", None) or str(
            getattr(source, "kind", "")
        )
        label = _clean_name(str(getattr(source, "label", "") or "")) or "Untitled"
        source_id = str(getattr(source, "source_id", "") or "").strip()
        available = bool(getattr(source, "available", True))
        # The goal is already the topic's stated objective; repeating it as a
        # readable material would only invite the tutor to "read" it.
        if kind == "goal":
            continue
        if not available or not source_id:
            result.materials.append(
                TopicMaterial(
                    sid="",
                    kind=kind or "unknown",
                    name=label,
                    available=False,
                    note="marked unavailable when the topic was created",
                )
            )
            continue
        if kind == "knowledge_base":
            result.materials.append(
                TopicMaterial(
                    sid="",
                    kind=kind,
                    name=label,
                    note=f"search with rag: kb_name={source_id!r}",
                )
            )
            continue
        if kind == "file":
            # One document the learner picked out of a knowledge base. Its
            # text lives only inside that base's index, so it is searched,
            # not read.
            kb_name = str((getattr(source, "metadata", None) or {}).get("kb_name") or "").strip()
            where = f"kb_name={kb_name!r}" if kb_name else "the attached knowledge base"
            result.materials.append(
                TopicMaterial(
                    sid="",
                    kind=kind,
                    name=label,
                    note=f"search with rag ({where}); this goal uses only this document",
                )
            )
            continue
        result.materials.append(
            TopicMaterial(
                sid="",
                kind=kind or "unknown",
                name=label,
                available=False,
                note="this material type cannot be read during tutoring",
            )
        )
    return result


def render_topic_manifest(materials: TopicMaterials) -> tuple[str, dict[str, str]]:
    """Render the manifest block and the ``read_source`` index.

    The closing rule is the whole point of the block: an unreadable material
    must be *named* as unreadable, so the tutor answers "I can see the outline
    but not the text" instead of asserting it has read a book it never saw.
    """
    if materials.is_empty():
        return "", {}

    rows: list[str] = []
    for material in materials.materials:
        if material.readable:
            row = (
                f"- id={material.sid}  type={material.kind}  name={material.name!r}"
                f"  size={_format_size(len(material.full_text))}"
            )
        elif material.available and material.note:
            row = f"- type={material.kind}  name={material.name!r}  {material.note}"
        else:
            row = (
                f"- type={material.kind}  name={material.name!r}"
                f"  unavailable: {material.note or 'unknown reason'}"
            )
        if material.outline:
            row += f"\n  about: {material.outline!r}"
        rows.append(row)

    header = (
        "[Topic Materials]\n"
        "The materials the learner chose for this mastery topic. They are the "
        "ground truth for this topic — teach from them, not from memory.\n"
        "- Rows marked `search with rag` are knowledge bases: query them with the "
        "rag tool using the kb_name shown.\n"
        "- Rows marked `unavailable` cannot be read at all. Never describe or "
        "quote their contents. Say plainly that the material is not readable and "
        "offer to teach from what is available."
    )
    return header + "\n\n" + "\n\n".join(rows), materials.source_index()


__all__ = [
    "TopicMaterial",
    "TopicMaterials",
    "build_topic_materials",
    "render_topic_manifest",
]
