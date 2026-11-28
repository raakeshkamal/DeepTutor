import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

function source(file: string): string {
  return readFileSync(path.resolve(process.cwd(), file), "utf8");
}

/**
 * AssistantResponse is shared by every chat surface and reads both viewer
 * contexts even when a mastery turn has no reading attachment.
 * Missing the provider makes an existing assistant message throw during
 * render, before the bare `/sessions` route can initialise its new session.
 */
test("the mastery study route provides every shared chat viewer context", () => {
  const layout = source("app/(workspace)/layout.tsx");
  const sessionLayout = source("app/(workspace)/learning/mastery/[pathId]/sessions/layout.tsx");
  assert.doesNotMatch(sessionLayout, /ChatRuntimeProvider|ReadingProvider|WatchingProvider/);
  assert.match(sessionLayout, /<QuizFollowupProvider>/);
  assert.match(sessionLayout, /<GeogebraTabProvider>/);
  const response = source("components/common/AssistantResponse.tsx");

  assert.match(response, /useReading\(\)/);
  assert.match(layout, /import \{ ReadingProvider \}/);
  assert.match(layout, /<ReadingProvider>/);
  assert.match(layout, /<ChatRuntimeProvider>/);
});

test("mastery study keeps the transcript flow and drops deleted features", () => {
  const study = source("components/space/learning/MasteryStudy.tsx");

  assert.match(study, /<TurnNavigator/);
  assert.match(study, /data-chat-column="true"/);
  assert.match(study, /<ChatMessageList/);
  // The cleanup removed notebooks, partner/notes research outlines and the
  // calendar runtime. None of them may be pulled back into the mastery page.
  assert.doesNotMatch(study, /SaveToNotebookModal|buildConversationNotebookSave/);
  assert.doesNotMatch(study, /useResearchOutlineContinuation/);
  assert.doesNotMatch(source("app/layout.tsx"), /SettingsReturnTracker/);
  assert.doesNotMatch(source("app/(workspace)/layout.tsx"), /CalendarRuntime/);
});
