"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createAnalysisStream } from "@/lib/api";
import type { AnalysisResult, AnalysisStatus, Finding } from "@/lib/types";

interface StreamState {
  status: AnalysisStatus | null;
  findings: Finding[];
  result: AnalysisResult | null;
  error: string | null;
  isStreaming: boolean;
  isComplete: boolean;
}

export function useAnalysisStream(analysisId: string | null) {
  const [state, setState] = useState<StreamState>({
    status: null,
    findings: [],
    result: null,
    error: null,
    isStreaming: false,
    isComplete: false,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const startStream = useCallback(() => {
    if (!analysisId) return;

    setState((prev) => ({ ...prev, isStreaming: true, error: null }));

    const es = createAnalysisStream(analysisId);
    eventSourceRef.current = es;

    es.addEventListener("status", (event) => {
      const data = JSON.parse(event.data);
      setState((prev) => ({ ...prev, status: data }));
    });

    es.addEventListener("finding", (event) => {
      const finding: Finding = JSON.parse(event.data);
      setState((prev) => ({
        ...prev,
        findings: [...prev.findings, finding],
      }));
    });

    es.addEventListener("complete", (event) => {
      const result: AnalysisResult = JSON.parse(event.data);
      setState((prev) => ({
        ...prev,
        result,
        findings: result.findings,
        isStreaming: false,
        isComplete: true,
      }));
      es.close();
    });

    es.addEventListener("error", (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data);
        setState((prev) => ({
          ...prev,
          error: data.message,
          isStreaming: false,
        }));
      } catch {
        setState((prev) => ({
          ...prev,
          error: "Connection lost",
          isStreaming: false,
        }));
      }
      es.close();
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        setState((prev) => {
          if (prev.isComplete) return prev;
          return { ...prev, isStreaming: false, error: "Stream ended unexpectedly" };
        });
      }
    };
  }, [analysisId]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  return { ...state, startStream };
}
