"use client";

/**
 * Mastery-only build: the notebook editor is gone. The retained session
 * viewer still offers a "notes" tab slot, so this keeps the slot mountable
 * without importing any deleted notes code.
 */
import { useTranslation } from "react-i18next";

export default function ChatMarkdownNoteTab({ sessionId }: { sessionId: string | null }) {
  const { t } = useTranslation();
  void sessionId;
  return (
    <div className="p-4 text-sm text-[var(--muted-foreground)]">
      {t("Notes are not available in the mastery-only build.")}
    </div>
  );
}
