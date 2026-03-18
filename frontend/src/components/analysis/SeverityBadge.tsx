import { Badge } from "@/components/ui/badge";
import type { Severity } from "@/lib/types";
import { AlertTriangle, AlertCircle, Info, CheckCircle } from "lucide-react";

const config: Record<Severity, { color: string; icon: typeof AlertTriangle; label: string }> = {
  critical: { color: "bg-red-500/15 text-red-400 border-red-500/30", icon: AlertCircle, label: "Critical" },
  warning: { color: "bg-amber-500/15 text-amber-400 border-amber-500/30", icon: AlertTriangle, label: "Warning" },
  info: { color: "bg-blue-500/15 text-blue-400 border-blue-500/30", icon: Info, label: "Info" },
  pass: { color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: CheckCircle, label: "Pass" },
};

export function SeverityBadge({ severity, showIcon = true }: { severity: Severity; showIcon?: boolean }) {
  const { color, icon: Icon, label } = config[severity] || config.info;
  return (
    <Badge variant="outline" className={`${color} font-medium gap-1`}>
      {showIcon && <Icon className="h-3 w-3" />}
      {label}
    </Badge>
  );
}
