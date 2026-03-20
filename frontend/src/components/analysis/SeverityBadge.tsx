import type { Severity } from "@/lib/types";

const config: Record<Severity, { bg: string; text: string; icon: string; label: string }> = {
  critical: { bg: "bg-red-500/15 border-red-500/30", text: "text-red-400", icon: "error", label: "Critical" },
  warning: { bg: "bg-amber-500/15 border-amber-500/30", text: "text-amber-400", icon: "warning", label: "Warning" },
  info: { bg: "bg-blue-500/15 border-blue-500/30", text: "text-blue-400", icon: "info", label: "Info" },
  pass: { bg: "bg-emerald-500/15 border-emerald-500/30", text: "text-emerald-400", icon: "check_circle", label: "Pass" },
};

export function SeverityBadge({ severity, showIcon = true }: { severity: Severity; showIcon?: boolean }) {
  const { bg, text, icon, label } = config[severity] || config.info;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase tracking-wider font-[var(--font-headline-stack)] ${bg} ${text}`}>
      {showIcon && <span className="material-symbols-outlined text-xs">{icon}</span>}
      {label}
    </span>
  );
}
