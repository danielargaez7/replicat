const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadBundle(file: File): Promise<{ analysis_id: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export function createAnalysisStream(analysisId: string): EventSource {
  return new EventSource(`${API_BASE}/api/analysis/${analysisId}/stream`);
}

export async function getAnalysis(analysisId: string) {
  const res = await fetch(`${API_BASE}/api/analysis/${analysisId}`);
  if (!res.ok) throw new Error("Analysis not found");
  return res.json();
}

export async function sendChatMessage(analysisId: string, message: string) {
  const res = await fetch(`${API_BASE}/api/analysis/${analysisId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

export async function getLogFile(analysisId: string, logPath: string) {
  const res = await fetch(
    `${API_BASE}/api/analysis/${analysisId}/logs?path=${encodeURIComponent(logPath)}`
  );
  if (!res.ok) throw new Error("Failed to fetch log file");
  return res.json();
}
