"use client";

/**
 * Mastery-only build: partner navigation was removed. The retained
 * CategoryNavigation lazily imports this named export, so keep a small
 * inert panel rather than restoring a deleted feature wholesale.
 */
export function PartnerNavigation({ active = true }: { active?: boolean }) {
  void active;
  return null;
}
