"use client";

/**
 * Mastery-only build: partner and partner-group consultations are gone.
 * Saved traces still need to render, so the retained subagent transcript
 * view handles every tab and no partner UI is imported.
 */
import type { StreamEvent } from "@/features/chat/model/protocol";
import SubagentTabBody from "./SubagentTabBody";

export default function ConsultationTabBody({
  tabEvents,
  sessionId,
}: {
  tabEvents: StreamEvent[];
  sessionId: string | null;
}) {
  return <SubagentTabBody tabEvents={tabEvents} sessionId={sessionId} />;
}
