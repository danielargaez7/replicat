"use client";

interface SeverityDonutProps {
  counts: { critical: number; warning: number; info: number; pass: number };
}

export function SeverityDonut({ counts }: SeverityDonutProps) {
  const total = counts.critical + counts.warning + counts.info + counts.pass;
  const r = 54;
  const circumference = 2 * Math.PI * r;

  if (total === 0) {
    return (
      <div className="relative w-32 h-32">
        <svg className="w-full h-full" viewBox="0 0 128 128">
          <circle
            className="text-surface-container-highest"
            cx="64" cy="64" r={r}
            fill="transparent"
            stroke="currentColor"
            strokeWidth="20"
          />
        </svg>
      </div>
    );
  }

  // Calculate dash offsets for each segment
  const critPct = counts.critical / total;
  const warnPct = counts.warning / total;
  const infoPct = (counts.info + counts.pass) / total;

  const critDash = critPct * circumference;
  const warnDash = warnPct * circumference;
  const infoDash = infoPct * circumference;

  // Rotation offsets (in degrees) — each segment starts where the previous ended
  const critRotation = -90; // start at top
  const warnRotation = critRotation + critPct * 360;
  const infoRotation = warnRotation + warnPct * 360;

  return (
    <div className="relative w-32 h-32">
      <svg className="w-full h-full" viewBox="0 0 128 128">
        {/* Critical (red) */}
        {critDash > 0 && (
          <circle
            cx="64" cy="64" r={r}
            fill="transparent"
            stroke="#93000a"
            strokeWidth="20"
            strokeDasharray={`${critDash} ${circumference - critDash}`}
            transform={`rotate(${critRotation} 64 64)`}
          />
        )}
        {/* Warning (purple) */}
        {warnDash > 0 && (
          <circle
            cx="64" cy="64" r={r}
            fill="transparent"
            stroke="#9a7bff"
            strokeWidth="20"
            strokeDasharray={`${warnDash} ${circumference - warnDash}`}
            transform={`rotate(${warnRotation} 64 64)`}
          />
        )}
        {/* Info (gray) */}
        {infoDash > 0 && (
          <circle
            cx="64" cy="64" r={r}
            fill="transparent"
            stroke="#484949"
            strokeWidth="20"
            strokeDasharray={`${infoDash} ${circumference - infoDash}`}
            transform={`rotate(${infoRotation} 64 64)`}
          />
        )}
      </svg>
    </div>
  );
}
