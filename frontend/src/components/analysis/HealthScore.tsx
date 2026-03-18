"use client";

function scoreColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number) {
  if (score >= 80) return "stroke-emerald-400/20";
  if (score >= 50) return "stroke-amber-400/20";
  return "stroke-red-400/20";
}

function scoreStroke(score: number) {
  if (score >= 80) return "stroke-emerald-400";
  if (score >= 50) return "stroke-amber-400";
  return "stroke-red-400";
}

function scoreLabel(score: number) {
  if (score >= 90) return "Healthy";
  if (score >= 70) return "Degraded";
  if (score >= 40) return "Unhealthy";
  return "Critical";
}

export function HealthScore({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" strokeWidth="8" className={scoreBg(score)} />
          <circle
            cx="50" cy="50" r="45" fill="none" strokeWidth="8"
            className={`${scoreStroke(score)} transition-all duration-1000`}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${scoreColor(score)}`}>{score}</span>
        </div>
      </div>
      <span className={`text-sm font-medium ${scoreColor(score)}`}>
        {scoreLabel(score)}
      </span>
    </div>
  );
}
