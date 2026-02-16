import type { AgentStatus, EventType } from "../../types/controlPlane";

interface BadgeProps {
  label: string;
  tone?: "neutral" | "ok" | "warn" | "danger" | "accent";
}

function toneClass(tone: NonNullable<BadgeProps["tone"]>): string {
  switch (tone) {
    case "ok":
      return "border-ok/50 bg-ok/15 text-[#7ee787]";
    case "warn":
      return "border-warn/50 bg-warn/15 text-[#e3b341]";
    case "danger":
      return "border-danger/50 bg-danger/15 text-[#ff7b72]";
    case "accent":
      return "border-accent/45 bg-accent/15 text-[#79c0ff]";
    default:
      return "border-border bg-panelAlt text-textMuted";
  }
}

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide border ${toneClass(tone)}`}
    >
      {label}
    </span>
  );
}

export function statusTone(status: AgentStatus): BadgeProps["tone"] {
  if (status === "ACTIVE") return "ok";
  if (status === "DRIFTING") return "warn";
  return "danger";
}

export function eventTone(type: EventType): BadgeProps["tone"] {
  if (type === "MUTATION LOOSEN" || type === "REDEEMED") return "ok";
  if (type === "MUTATION TIGHTEN" || type === "DRIFT DETECTED") return "warn";
  if (type === "SUPPRESSED" || type === "CIRCUIT BREAKER") return "danger";
  return "neutral";
}
