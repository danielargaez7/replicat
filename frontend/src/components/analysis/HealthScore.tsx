"use client";

function scoreColor(score: number) {
  if (score >= 80) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-primary-container";
}

function scoreBg(score: number) {
  if (score >= 80) return "stroke-emerald-400/15";
  if (score >= 50) return "stroke-amber-400/15";
  return "stroke-primary-container/15";
}

function scoreStroke(score: number) {
  if (score >= 80) return "stroke-emerald-400";
  if (score >= 50) return "stroke-amber-400";
  return "stroke-primary-container";
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
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" strokeWidth="6" className={scoreBg(score)} />
          <circle
            cx="50" cy="50" r="45" fill="none" strokeWidth="6"
            className={`${scoreStroke(score)} transition-all duration-1000`}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold font-[var(--font-headline-stack)] ${scoreColor(score)}`}>
            {score}
          </span>
        </div>
      </div>
      <span className={`font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest ${scoreColor(score)}`}>
        {scoreLabel(score)}
      </span>
    </div>
  );
}
