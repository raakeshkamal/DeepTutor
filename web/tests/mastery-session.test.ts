import assert from "node:assert/strict";
import test from "node:test";

import {
  masteryPathIdOf,
  readingWorkspaceIdOf,
  sessionRoute,
} from "../lib/mastery-session";
import type { SessionSummary } from "../lib/session-api";

function session(preferences: SessionSummary["preferences"]): SessionSummary {
  return {
    id: "session-1",
    session_id: "session-1",
    title: "Learning session",
    created_at: 1,
    updated_at: 1,
    message_count: 1,
    last_message: "hello",
    preferences,
  };
}

// Mastery-only regression: there is exactly one surface route. Reading,
// books, notes and watching were removed with their features, so their
// legacy helpers must never claim a conversation again.
test("mastery ownership survives switching the per-turn action", () => {
  const item = session({
    workspace_mode: "mastery_path",
    mastery_path_id: "path-42",
    capability: "deep_research",
  });
  assert.equal(masteryPathIdOf(item), "path-42");
});

test("a mastery conversation routes back to its topic session", () => {
  const item = session({
    workspace_mode: "mastery_path",
    mastery_path_id: "path-42",
  });
  assert.match(
    sessionRoute(item),
    /^\/learning\/mastery\/path-42\/sessions\/session-1/,
  );
});

test("capability alone never claims workspace ownership", () => {
  assert.equal(
    masteryPathIdOf(session({ capability: "mastery_path", mastery_path_id: "legacy-path" })),
    "",
  );
  assert.equal(
    readingWorkspaceIdOf(session({ capability: "immersive_reading", reading_workspace_id: "legacy" })),
    "",
  );
});

test("unrelated sessions fall back to /chat and never inherit stale ids", () => {
  assert.equal(
    masteryPathIdOf(session({ capability: "chat", mastery_path_id: "stale-path" })),
    "",
  );
  assert.match(
    sessionRoute(session({ capability: "chat", mastery_path_id: "stale-path" })),
    /^\/chat\/session-1/,
  );
  assert.equal(
    readingWorkspaceIdOf(session({ workspace_mode: "immersive_reading", reading_workspace_id: "rw_42" })),
    "",
  );
  assert.match(
    sessionRoute(session({ note_document_id: "0c2d24985c4f" })),
    /^\/chat\/session-1/,
  );
});
