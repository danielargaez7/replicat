"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Upload,
  FileArchive,
  Cpu,
  Shield,
  Zap,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
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
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Cpu className="h-4 w-4 text-primary-foreground" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Bundlescope</h1>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            beta
          </span>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <div className="max-w-2xl w-full text-center space-y-6">
          <div className="space-y-3">
            <h2 className="text-4xl font-bold tracking-tight">
              AI-Powered Bundle Analysis
            </h2>
            <p className="text-muted-foreground text-lg max-w-lg mx-auto">
              Upload a Kubernetes Troubleshoot support bundle. Get root cause
              analysis, evidence-grounded findings, and remediation steps in
              seconds.
            </p>
          </div>

          {/* Upload Zone */}
          <Card
            className={`transition-all duration-200 ${
              isDragOver
                ? "border-primary bg-primary/5 scale-[1.02]"
                : "border-dashed hover:border-primary/50"
            } ${isUploading ? "pointer-events-none opacity-80" : "cursor-pointer"}`}
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
            <CardContent className="py-12 flex flex-col items-center gap-4">
              {isUploading ? (
                <>
                  <FileArchive className="h-12 w-12 text-primary animate-pulse" />
                  <div className="space-y-2 w-full max-w-xs">
                    <p className="text-sm text-muted-foreground">
                      Uploading bundle...
                    </p>
                    <Progress value={uploadProgress} className="h-2" />
                  </div>
                </>
              ) : (
                <>
                  <Upload
                    className={`h-12 w-12 ${
                      isDragOver ? "text-primary" : "text-muted-foreground"
                    }`}
                  />
                  <div className="space-y-1">
                    <p className="font-medium">
                      Drop your support bundle here
                    </p>
                    <p className="text-sm text-muted-foreground">
                      or click to browse &mdash; accepts .tar.gz and .tgz
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <input
            id="file-input"
            type="file"
            accept=".tar.gz,.tgz"
            className="hidden"
            onChange={handleFileInput}
          />

          {error && (
            <div className="flex items-center gap-2 text-destructive text-sm justify-center">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          )}

          {/* Features */}
          <div className="grid grid-cols-3 gap-4 pt-8">
            <div className="text-center space-y-2 p-4">
              <Zap className="h-5 w-5 mx-auto text-amber-400" />
              <p className="text-sm font-medium">4-Pass Analysis</p>
              <p className="text-xs text-muted-foreground">
                Heuristic triage, AI deep analysis, root cause synthesis, and
                remediation
              </p>
            </div>
            <div className="text-center space-y-2 p-4">
              <Shield className="h-5 w-5 mx-auto text-emerald-400" />
              <p className="text-sm font-medium">Evidence-Grounded</p>
              <p className="text-xs text-muted-foreground">
                Every finding cites actual log lines, events, and config from
                your bundle
              </p>
            </div>
            <div className="text-center space-y-2 p-4">
              <Cpu className="h-5 w-5 mx-auto text-blue-400" />
              <p className="text-sm font-medium">Real-Time Streaming</p>
              <p className="text-xs text-muted-foreground">
                Watch findings appear live as the analysis engine works through
                your cluster
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
