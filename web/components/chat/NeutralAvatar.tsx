"use client";

/**
 * Neutral answerer mark for the mastery-only build.
 *
 * Partners, partner groups and connected agents were removed by the cleanup,
 * but the retained chat message renderers still need *some* avatar for a
 * trace's answerer. This is a small, dependency-free replacement: an initial
 * (or the turn's emoji) on a coloured tile. No partner API is consulted.
 */

export interface NeutralAvatarProps {
  name?: string;
  emoji?: string | null;
  color?: string | null;
  image?: string | null;
  size?: number;
  className?: string;
}

export default function NeutralAvatar({
  name = "",
  emoji,
  color,
  image,
  size = 16,
  className = "",
}: NeutralAvatarProps) {
  const label = (emoji || "").trim() || (name || "T").trim().charAt(0).toUpperCase() || "T";
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-full text-xs font-medium text-white ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: color || "var(--muted-foreground)",
        ...(image ? { backgroundImage: `url(${image})`, backgroundSize: "cover" } : {}),
      }}
    >
      {image ? "" : label}
    </span>
  );
}
