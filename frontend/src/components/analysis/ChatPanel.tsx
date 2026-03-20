"use client";

import { useCallback, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { sendChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTED_QUESTIONS = [
  "What's the most critical issue?",
  "What should I fix first?",
  "Summarize all findings",
  "Are any nodes unhealthy?",
];

export function ChatPanel({ analysisId }: { analysisId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const res = await sendChatMessage(analysisId, text.trim());
        const assistantMsg: Message = { role: "assistant", content: res.response };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Failed to get response. Check your API key." },
        ]);
      } finally {
        setIsLoading(false);
        setTimeout(() => {
          scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
        }, 100);
      }
    },
    [analysisId, isLoading]
  );

  return (
    <div className="flex flex-col h-[calc(100vh-350px)]">
      <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
        <div className="space-y-4 py-4">
          {messages.length === 0 && (
            <div className="text-center space-y-6 py-8">
              <span className="material-symbols-outlined text-4xl text-on-surface/20">
                auto_awesome
              </span>
              <p className="text-sm text-on-surface/40">
                Ask questions about this support bundle analysis
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="px-4 py-2 rounded-lg border border-outline-variant/20 bg-surface-container/60 text-xs text-on-surface/50 hover:text-on-surface hover:border-primary-container/30 hover:bg-surface-container-high/50 transition-all font-[var(--font-headline-stack)] uppercase tracking-wider font-bold"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
            >
              {msg.role === "assistant" && (
                <div className="h-8 w-8 rounded-lg bg-md3-tertiary/10 flex items-center justify-center shrink-0 mt-0.5 border border-md3-tertiary/20">
                  <span className="material-symbols-outlined text-md3-tertiary text-base">
                    smart_toy
                  </span>
                </div>
              )}
              <div
                className={`rounded-xl px-4 py-3 max-w-[80%] text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "signature-gradient text-on-primary"
                    : "glass-card"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
              {msg.role === "user" && (
                <div className="h-8 w-8 rounded-lg bg-surface-container-highest flex items-center justify-center shrink-0 mt-0.5 border border-outline-variant/20">
                  <span className="material-symbols-outlined text-on-surface/50 text-base">
                    person
                  </span>
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-md3-tertiary/10 flex items-center justify-center shrink-0 border border-md3-tertiary/20">
                <span className="material-symbols-outlined text-md3-tertiary text-base">
                  smart_toy
                </span>
              </div>
              <div className="glass-card rounded-xl px-4 py-3">
                <span className="material-symbols-outlined text-on-surface/40 text-base animate-spin">
                  progress_activity
                </span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-outline-variant/10 pt-4 mt-auto">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the analysis..."
            className="flex-1 min-h-[44px] max-h-32 resize-none bg-surface-container/60 backdrop-blur-md border border-outline-variant/20 rounded-lg px-4 py-3 text-sm text-on-surface placeholder:text-on-surface/30 focus:outline-none focus:border-primary-container/50 focus:ring-1 focus:ring-primary-container/20 transition-all"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || isLoading}
            className="shrink-0 h-11 w-11 rounded-lg signature-gradient flex items-center justify-center shadow-[0_0_15px_rgba(255,82,96,0.2)] disabled:opacity-30 disabled:shadow-none active:scale-95 transition-all"
          >
            <span className="material-symbols-outlined text-on-primary text-base">send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
