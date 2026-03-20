"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { uploadBundle } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".tar.gz") && !file.name.endsWith(".tgz")) {
        setError("Please upload a .tar.gz or .tgz support bundle");
        return;
      }

      setIsUploading(true);
      setError(null);
      setUploadProgress(10);

      try {
        const interval = setInterval(() => {
          setUploadProgress((p) => Math.min(p + 5, 90));
        }, 200);

        const { analysis_id } = await uploadBundle(file);
        clearInterval(interval);
        setUploadProgress(100);

        setTimeout(() => {
          router.push(`/analysis/${analysis_id}`);
        }, 300);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setIsUploading(false);
        setUploadProgress(0);
      }
    },
    [router]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="relative z-10 min-h-screen flex flex-col">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-surface/60 backdrop-blur-xl border-b border-surface-variant/30 shadow-[0_0_15px_rgba(255,82,96,0.05)]">
        <div className="max-w-screen-2xl mx-auto px-8 py-4 flex justify-between items-center w-full">
          <div className="text-2xl font-bold tracking-tighter text-primary-container uppercase font-[var(--font-headline-stack)]">
            Bundlescope
          </div>
          <div className="hidden md:flex gap-8 items-center">
            <a
              className="font-[var(--font-headline-stack)] tracking-tight font-bold uppercase text-[0.75rem] text-primary-container border-b-2 border-primary-container pb-1"
              href="#"
            >
              Product
            </a>
            <a
              className="font-[var(--font-headline-stack)] tracking-tight font-bold uppercase text-[0.75rem] text-on-surface hover:text-md3-primary transition-colors"
              href="#"
            >
              Resources
            </a>
            <a
              className="font-[var(--font-headline-stack)] tracking-tight font-bold uppercase text-[0.75rem] text-on-surface hover:text-md3-primary transition-colors"
              href="#"
            >
              Documentation
            </a>
          </div>
          <div className="flex items-center gap-4">
            <button className="font-[var(--font-headline-stack)] tracking-tight font-bold uppercase text-[0.75rem] text-on-surface hover:text-primary-container transition-colors">
              Sign In
            </button>
            <button className="signature-gradient px-6 py-2 rounded-lg font-[var(--font-headline-stack)] tracking-tight font-bold uppercase text-[0.75rem] text-on-primary shadow-[0_0_15px_rgba(255,82,96,0.3)] active:scale-95 transition-transform">
              Get Demo
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 pt-32 pb-24">
        {/* Hero Section */}
        <section className="max-w-7xl mx-auto px-8 mb-24">
          <div className="text-center mb-16">
            <h1 className="font-[var(--font-headline-stack)] text-5xl md:text-7xl font-bold tracking-tighter mb-6 leading-none">
              DECODE THE{" "}
              <span className="text-primary-container">K8S VOID</span>
            </h1>
            <p className="text-on-surface/70 max-w-2xl mx-auto text-lg backdrop-blur-sm inline-block p-4 rounded-xl">
              Instant analysis for Kubernetes support bundles. Upload your
              .tar.gz and let Bundlescope AI pinpoint cluster degradations in
              seconds.
            </p>
          </div>

          {/* Upload Zone */}
          <div className="max-w-4xl mx-auto">
            <div className="relative group">
              {/* Glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-primary-container/20 to-md3-tertiary/20 rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />

              <div
                className={`relative bg-surface-container-high/60 backdrop-blur-md border-2 border-dashed rounded-xl py-8 px-16 flex flex-col items-center justify-center text-center transition-all duration-300 ${
                  isDragOver
                    ? "border-primary-container/80 bg-primary-container/5 scale-[1.01]"
                    : "border-outline-variant/30 hover:border-primary-container/50"
                } ${isUploading ? "pointer-events-none" : "cursor-pointer"}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => {
                  if (!isUploading) {
                    document.getElementById("file-input")?.click();
                  }
                }}
              >
                <div className="w-16 h-16 bg-surface-container-lowest rounded-full flex items-center justify-center mb-4 border border-outline-variant/10 shadow-inner">
                  <span className="material-symbols-outlined text-primary-container text-4xl">
                    upload_file
                  </span>
                </div>

                {isUploading ? (
                  <>
                    <h2 className="font-[var(--font-headline-stack)] text-2xl font-bold mb-2">
                      Uploading bundle...
                    </h2>
                    <p className="text-on-surface/40 mb-4 font-[var(--font-headline-stack)] text-sm tracking-widest uppercase">
                      Processing your support bundle
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="font-[var(--font-headline-stack)] text-2xl font-bold mb-2">
                      Drag and drop .tar.gz
                    </h2>
                    <p className="text-on-surface/40 mb-4 font-[var(--font-headline-stack)] text-sm tracking-widest uppercase">
                      Support bundle max size 500MB
                    </p>
                  </>
                )}

                {!isUploading && (
                  <button className="bg-surface-container-highest/80 px-8 py-3 rounded-lg border border-outline-variant/20 hover:border-primary-container/50 hover:bg-surface-bright transition-all active:scale-95">
                    <span className="font-[var(--font-headline-stack)] font-bold uppercase text-xs tracking-widest flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm">
                        folder_open
                      </span>
                      Browse Files
                    </span>
                  </button>
                )}

                {/* Progress Bar */}
                <div className="w-full max-w-md mt-6">
                  <div className="flex justify-between items-center mb-2 px-1">
                    <span className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-on-surface/40">
                      {isUploading ? "Uploading" : "Waiting for upload"}
                    </span>
                    <span className="font-[var(--font-headline-stack)] text-[10px] uppercase tracking-widest text-md3-primary">
                      {uploadProgress}%
                    </span>
                  </div>
                  <div className="h-[2px] w-full bg-surface-container-lowest overflow-hidden rounded-full">
                    <div
                      className="h-full bg-primary-container transition-all duration-500 relative"
                      style={{ width: `${uploadProgress}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <input
            id="file-input"
            type="file"
            accept=".tar.gz,.tgz"
            className="hidden"
            onChange={handleFileInput}
          />

          {error && (
            <div className="max-w-4xl mx-auto mt-4 flex items-center gap-2 text-md3-error text-sm justify-center bg-error-container/10 border border-md3-error/20 rounded-lg px-4 py-3">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}
        </section>

        {/* Features Bento Grid */}
        <section className="max-w-7xl mx-auto px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass-card rounded-xl p-8 hover:border-md3-primary/20 hover:bg-surface-bright/80 transition-all duration-300 group">
              <div className="w-12 h-12 glass-panel rounded-lg flex items-center justify-center mb-6 border border-outline-variant/10 group-hover:shadow-[0_0_15px_rgba(255,179,179,0.1)]">
                <span className="material-symbols-outlined text-primary-container">
                  psychology
                </span>
              </div>
              <h3 className="font-[var(--font-headline-stack)] text-xl font-bold mb-4 tracking-tight uppercase">
                4-Pass Analysis
              </h3>
              <p className="text-on-surface/60 text-sm leading-relaxed">
                Our multi-stage neural engine dissects logs, events, and metrics
                in parallel to eliminate false positives.
              </p>
            </div>

            <div className="glass-card rounded-xl p-8 hover:border-md3-primary/20 hover:bg-surface-bright/80 transition-all duration-300 group">
              <div className="w-12 h-12 glass-panel rounded-lg flex items-center justify-center mb-6 border border-outline-variant/10 group-hover:shadow-[0_0_15px_rgba(255,179,179,0.1)]">
                <span className="material-symbols-outlined text-primary-container">
                  shield
                </span>
              </div>
              <h3 className="font-[var(--font-headline-stack)] text-xl font-bold mb-4 tracking-tight uppercase">
                Evidence-Grounded
              </h3>
              <p className="text-on-surface/60 text-sm leading-relaxed">
                Every diagnostic result is backed by direct pointers to relevant
                lines in your bundle files.
              </p>
            </div>

            <div className="glass-card rounded-xl p-8 hover:border-md3-primary/20 hover:bg-surface-bright/80 transition-all duration-300 group">
              <div className="w-12 h-12 glass-panel rounded-lg flex items-center justify-center mb-6 border border-outline-variant/10 group-hover:shadow-[0_0_15px_rgba(255,179,179,0.1)]">
                <span className="material-symbols-outlined text-primary-container">
                  bolt
                </span>
              </div>
              <h3 className="font-[var(--font-headline-stack)] text-xl font-bold mb-4 tracking-tight uppercase">
                Real-Time Streaming
              </h3>
              <p className="text-on-surface/60 text-sm leading-relaxed">
                View analysis results as they arrive. No need to wait for the
                entire bundle to be processed.
              </p>
            </div>
          </div>
        </section>

        {/* Technical Context Area */}
        <section className="mt-32 max-w-7xl mx-auto px-8 relative">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7">
              <div className="inline-block px-3 py-1 rounded-full bg-surface-container-highest/80 backdrop-blur-sm border border-outline-variant/20 mb-6">
                <span className="font-[var(--font-headline-stack)] text-[10px] font-bold text-md3-primary uppercase tracking-[0.2em]">
                  Infrastructure Intelligence
                </span>
              </div>
              <h2 className="font-[var(--font-headline-stack)] text-4xl md:text-5xl font-bold mb-8 tracking-tighter leading-tight">
                DESIGNED FOR THE <br />
                <span className="text-md3-tertiary">CLOUD-NATIVE ERA</span>
              </h2>
              <div className="space-y-6">
                <div className="flex gap-4 items-start">
                  <div className="mt-1 w-2 h-2 rounded-full bg-primary-container shrink-0" />
                  <div>
                    <h4 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm mb-1 tracking-wider">
                      Automated Correlation
                    </h4>
                    <p className="text-on-surface/50 text-sm">
                      Mapping OOMKills to specific node pressure events across
                      the entire cluster lifecycle.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4 items-start">
                  <div className="mt-1 w-2 h-2 rounded-full bg-md3-tertiary shrink-0" />
                  <div>
                    <h4 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm mb-1 tracking-wider">
                      Security First
                    </h4>
                    <p className="text-on-surface/50 text-sm">
                      Local-first processing options and automatic PII masking
                      for sensitive configuration data.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4 items-start">
                  <div className="mt-1 w-2 h-2 rounded-full bg-primary-container shrink-0" />
                  <div>
                    <h4 className="font-[var(--font-headline-stack)] font-bold uppercase text-sm mb-1 tracking-wider">
                      Causal Chain Analysis
                    </h4>
                    <p className="text-on-surface/50 text-sm">
                      Connects findings into root-cause narratives. A caused B
                      caused C — fix A first.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:col-span-5 relative aspect-square">
              <div className="absolute inset-0 bg-surface-container-lowest/40 backdrop-blur-sm rounded-xl border border-outline-variant/20 overflow-hidden flex items-center justify-center">
                <div className="relative w-48 h-48">
                  <div className="absolute inset-0 border-2 border-md3-primary/30 rotate-45 transform" />
                  <div className="absolute inset-4 border border-md3-tertiary/40 -rotate-12 transform" />
                  <div className="absolute inset-8 border border-primary-container/20 rotate-12 transform" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-12 h-12 bg-primary-container blur-2xl opacity-40" />
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="material-symbols-outlined text-6xl text-primary-container/30">
                      hub
                    </span>
                  </div>
                </div>
              </div>
              <div className="absolute top-4 right-4 flex gap-2">
                <div className="w-2 h-2 rounded-full bg-md3-primary animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-md3-tertiary opacity-50" />
                <div className="w-2 h-2 rounded-full bg-md3-error opacity-50" />
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 bg-surface-container-lowest/80 backdrop-blur-md w-full py-12 border-t border-surface-variant/30">
        <div className="max-w-7xl mx-auto px-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex flex-col items-center md:items-start gap-2">
            <div className="font-[var(--font-headline-stack)] font-bold text-primary-container">
              Bundlescope
            </div>
            <div className="text-sm text-on-surface/60">
              Kubernetes Native Support Bundle Analysis.
            </div>
          </div>
          <div className="flex gap-8">
            <a className="text-sm text-on-surface/40 hover:text-primary-container transition-colors" href="#">
              Privacy Policy
            </a>
            <a className="text-sm text-on-surface/40 hover:text-primary-container transition-colors" href="#">
              Terms of Service
            </a>
            <a className="text-sm text-on-surface/40 hover:text-primary-container transition-colors" href="#">
              Security
            </a>
            <a className="text-sm text-on-surface/40 hover:text-primary-container transition-colors" href="#">
              Status
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
