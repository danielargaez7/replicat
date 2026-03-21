"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { RemediationPlan } from "@/lib/types";
import { getRemediationPlan, approveRemediation } from "@/lib/api";
import { RemediationCard } from "@/components/remediation/RemediationCard";
import { ActionBar } from "@/components/remediation/ActionBar";

export default function RemediatePage() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params.id as string;

  const [plan, setPlan] = useState<RemediationPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) return;
    setLoading(true);
    getRemediationPlan(analysisId)
      .then((data) => {
        setPlan(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [analysisId]);

  const handleApprove = useCallback(
    async (remediationId: string) => {
      if (!plan) return;
      try {
        await approveRemediation(analysisId, remediationId);
        setPlan({
          ...plan,
          items: plan.items.map((item) =>
            item.id === remediationId ? { ...item, approved: true } : item
          ),
        });
      } catch {
        // Silently handle — approval state will refresh on next load
      }
    },
    [analysisId, plan]
  );

  const hasApprovedItems = plan?.items.some((i) => i.approved) ?? false;

  if (loading) {
    return (
      <div className="relative z-10 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <span className="material-symbols-outlined text-4xl text-primary-container animate-pulse">
            healing
          </span>
          <p className="mt-4 font-[var(--font-headline-stack)] text-sm uppercase tracking-widest text-on-surface/40">
            Building remediation plan...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative z-10 min-h-screen flex items-center justify-center">
        <div className="glass-card rounded-xl p-8 max-w-md text-center">
          <span className="material-symbols-outlined text-4xl text-red-400">error</span>
          <p className="mt-4 text-on-surface/60">{error}</p>
          <button
            onClick={() => router.push(`/analysis/${analysisId}`)}
            className="mt-4 px-4 py-2 rounded-lg bg-surface-container-highest/60 border border-outline-variant/20 font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest"
          >
            Back to Analysis
          </button>
        </div>
      </div>
    );
  }

  if (!plan) return null;

  return (
    <div className="relative z-10 min-h-screen flex flex-col">
      {/* Header */}
      <header className="fixed top-0 w-full z-50 bg-surface/60 backdrop-blur-xl border-b border-surface-variant/30">
        <div className="max-w-screen-2xl mx-auto px-8 py-4 flex items-center gap-4">
          <button
            onClick={() => router.push(`/analysis/${analysisId}`)}
            className="flex items-center gap-1 text-on-surface/40 hover:text-primary-container transition-colors"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            <span className="font-[var(--font-headline-stack)] text-xs uppercase tracking-widest">
              Analysis
            </span>
          </button>
          <div className="h-4 w-px bg-outline-variant/20" />
          <h1 className="font-[var(--font-headline-stack)] text-lg font-bold tracking-tighter uppercase">
            Remediation Plan
          </h1>
          <div className="ml-auto flex items-center gap-3">
            <div className={`px-3 py-1 rounded-full text-xs font-bold ${
              plan.health_score >= 80 ? "bg-green-500/20 text-green-400" :
              plan.health_score >= 50 ? "bg-amber-500/20 text-amber-400" :
              "bg-red-500/20 text-red-400"
            }`}>
              Health: {plan.health_score}/100
            </div>
            <div className="px-3 py-1 rounded-full bg-surface-container-highest/60 text-xs text-on-surface/50">
              {plan.total_items} fix{plan.total_items !== 1 ? "es" : ""}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 pt-24 pb-24 max-w-5xl mx-auto w-full px-8">
        {/* Summary */}
        {(plan.summary || plan.root_cause) && (
          <div className="glass-card rounded-xl p-6 mb-8">
            {plan.root_cause && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-primary-container text-sm">
                    account_tree
                  </span>
                  <span className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-primary-container">
                    Root Cause
                  </span>
                </div>
                <p className="text-sm text-on-surface/70 leading-relaxed">{plan.root_cause}</p>
              </div>
            )}
            {plan.summary && (
              <p className="text-sm text-on-surface/50 leading-relaxed">{plan.summary}</p>
            )}
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="glass-panel rounded-xl p-4 text-center">
            <div className="font-[var(--font-headline-stack)] text-2xl font-bold text-primary-container">
              {plan.critical_count}
            </div>
            <div className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40">
              Critical
            </div>
          </div>
          <div className="glass-panel rounded-xl p-4 text-center">
            <div className="font-[var(--font-headline-stack)] text-2xl font-bold text-on-surface/70">
              {plan.total_items - plan.auto_resolve_count}
            </div>
            <div className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40">
              Action Required
            </div>
          </div>
          <div className="glass-panel rounded-xl p-4 text-center">
            <div className="font-[var(--font-headline-stack)] text-2xl font-bold text-green-400">
              {plan.auto_resolve_count}
            </div>
            <div className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40">
              Auto-Resolve
            </div>
          </div>
        </div>

        {/* Remediation items */}
        <div className="space-y-4 mb-8">
          <div className="flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-primary-container">checklist</span>
            <h2 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm tracking-tight">
              Ordered Fixes
            </h2>
            <span className="text-[10px] text-on-surface/30 font-[var(--font-headline-stack)] uppercase tracking-widest">
              Execute in order shown
            </span>
          </div>

          {plan.items.length === 0 ? (
            <div className="glass-card rounded-xl p-8 text-center">
              <span className="material-symbols-outlined text-4xl text-green-400">
                check_circle
              </span>
              <p className="mt-4 text-on-surface/50">
                No actionable remediations found. The cluster looks healthy.
              </p>
            </div>
          ) : (
            plan.items.map((item) => (
              <RemediationCard
                key={item.id}
                item={item}
                onApprove={handleApprove}
              />
            ))
          )}
        </div>

        {/* Action bar */}
        {plan.items.length > 0 && (
          <ActionBar analysisId={analysisId} hasApprovedItems={hasApprovedItems} />
        )}
      </main>
    </div>
  );
}
