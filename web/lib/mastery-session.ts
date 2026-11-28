import { scopedUrl } from "@/lib/workspace-scope";
import { sessionWorkspaceId } from "@/lib/session-api";
import { masterySessionRoute } from "@/lib/learning-routes";
/**
 * Which surface a conversation belongs to — the one place that decides.
 *
 * Mastery-only cleanup: there is exactly one surface route. A mastery study
 * conversation is an ordinary chat session that carries `mastery_path_id`
 * in its preferences; the sidebar files it under its topic and the click
 * handler opens it on that topic session route. Every other conversation
 * falls back to `/chat`.
 *
 * The helpers below are compatibility shims for the remaining sidebar and
 * chat callers. Reading, books, notes and watching no longer exist on this
 * branch, so they always report "no other surface" instead of importing
 * those modules.
 */

import type { SessionSummary } from "@/lib/session-api";

export function masteryPathIdOf(session: SessionSummary): string {
  const preferences = session.preferences;
  if (!preferences) return "";
  if (preferences.workspace_mode !== "mastery_path") return "";
  return String(preferences.mastery_path_id || "");
}

/** Deprecated: the reader is gone. Always empty on this branch. */
export function readingWorkspaceIdOf(_session: SessionSummary): string {
  return "";
}

/** Deprecated: books are gone. Always null on this branch. */
export function bookPageOf(
  _session: SessionSummary,
): { bookId: string; pageId: string } | null {
  return null;
}

/** Deprecated: notes are gone. Always empty on this branch. */
export function notePageIdOf(_session: SessionSummary): string {
  return "";
}

/** Deprecated: notes are gone. Always false on this branch. */
export function isNoteSession(_session: SessionSummary): boolean {
  return false;
}

/** Where clicking this conversation should land. */
export function sessionRoute(session: SessionSummary): string {
  return scopedUrl(surfaceRoute(session), sessionWorkspaceId(session));
}

function surfaceRoute(session: SessionSummary): string {
  const sessionId = encodeURIComponent(session.session_id);
  const pathId = masteryPathIdOf(session);
  if (pathId) {
    return masterySessionRoute(pathId, session.session_id, sessionWorkspaceId(session));
  }
  return `/chat/${sessionId}`;
}
