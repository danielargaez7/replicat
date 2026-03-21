"use client";

import { useState } from "react";
import { getPlaybookUrl } from "@/lib/api";

interface ActionBarProps {
  analysisId: string;
  hasApprovedItems: boolean;
}

export function ActionBar({ analysisId, hasApprovedItems }: ActionBarProps) {
  const [showHelmInstructions, setShowHelmInstructions] = useState(false);

  return (
    <div className="glass-card rounded-xl p-6 space-y-6">
      {/* Fix Online */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-primary-container">cloud</span>
          <h3 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm tracking-tight">
            Fix Online
          </h3>
        </div>

        {!showHelmInstructions ? (
          <div className="space-y-3">
            <p className="text-xs text-on-surface/50">
              Connect the Bundlescope Operator to your cluster to execute approved fixes remotely.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowHelmInstructions(true)}
                className="px-4 py-2 rounded-lg bg-surface-container-highest/60 border border-outline-variant/20 hover:border-primary-container/50 transition-all font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest active:scale-95"
              >
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">terminal</span>
                  Install Operator
                </span>
              </button>
              <button
                disabled={!hasApprovedItems}
                className={`px-4 py-2 rounded-lg font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest transition-all ${
                  hasApprovedItems
                    ? "signature-gradient text-on-primary shadow-[0_0_15px_rgba(255,82,96,0.3)] active:scale-95"
                    : "bg-surface-container-highest/40 text-on-surface/20 border border-outline-variant/10 cursor-not-allowed"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm">play_arrow</span>
                  Apply Approved Fixes
                </span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-on-surface/50">
              Run this command in your cluster to install the Bundlescope Operator:
            </p>
            <div className="relative bg-surface-container-lowest/60 rounded-lg border border-outline-variant/10 p-4 font-mono text-sm text-on-surface/80">
              <code>helm install bundlescope-operator oci://registry.bundlescope.io/operator --namespace bundlescope-system --create-namespace</code>
            </div>
            <p className="text-[10px] text-on-surface/30">
              The operator runs inside your cluster with scoped RBAC permissions. It maintains an outbound-only connection — no inbound firewall rules needed.
            </p>
            <button
              onClick={() => setShowHelmInstructions(false)}
              className="text-xs text-primary-container/60 hover:text-primary-container transition-colors"
            >
              Hide instructions
            </button>
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-outline-variant/10" />

      {/* Fix Offline */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-md3-tertiary">cloud_off</span>
          <h3 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm tracking-tight">
            Fix Offline
          </h3>
        </div>

        <p className="text-xs text-on-surface/50 mb-3">
          For air-gapped or restricted environments with no internet connectivity.
        </p>

        <div className="flex gap-3">
          <button
            disabled
            className="px-4 py-2 rounded-lg bg-surface-container-highest/40 border border-outline-variant/10 font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest text-on-surface/30 cursor-not-allowed"
            title="Coming soon"
          >
            <span className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">usb</span>
              Download CLI
              <span className="text-[8px] normal-case tracking-normal font-normal bg-surface-container-highest/60 px-1.5 py-0.5 rounded">
                Soon
              </span>
            </span>
          </button>

          <a
            href={getPlaybookUrl(analysisId)}
            download
            className="px-4 py-2 rounded-lg bg-surface-container-highest/60 border border-outline-variant/20 hover:border-md3-tertiary/50 transition-all font-[var(--font-headline-stack)] text-xs font-bold uppercase tracking-widest active:scale-95"
          >
            <span className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
              Export Playbook PDF
            </span>
          </a>
        </div>
      </div>
    </div>
  );
}
