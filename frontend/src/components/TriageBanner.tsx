import type { TriageLevel } from "../types/chat";

interface TriageBannerProps {
  level: TriageLevel;
}

const CONFIG: Record<TriageLevel, { label: string; classes: string }> = {
  emergency: {
    label: "Emergency guidance",
    classes: "bg-baymax-danger/15 text-baymax-danger border-baymax-danger/40",
  },
  distressed: {
    label: "Gentle response",
    classes: "bg-baymax-warn/15 text-baymax-warn border-baymax-warn/40",
  },
  routine: {
    label: "",
    classes: "",
  },
};

export function TriageBanner({ level }: TriageBannerProps) {
  if (level === "routine") return null;
  const { label, classes } = CONFIG[level];

  return (
    <div className={`mb-2 inline-block rounded-full border px-3 py-1 text-xs font-medium ${classes}`}>
      {label}
    </div>
  );
}
