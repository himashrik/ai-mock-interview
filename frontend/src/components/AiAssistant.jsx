import React, { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

export default function AiAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadedHistory, setLoadedHistory] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (open && !loadedHistory) {
      api
        .get("/assistant/messages")
        .then(setMessages)
        .catch(() => {})
        .finally(() => setLoadedHistory(true));
    }
  }, [open, loadedHistory]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);
    // Optimistically show the user's message immediately.
    setMessages((prev) => [...prev, { id: `temp-${Date.now()}`, role: "user", content: text }]);

    try {
      const reply = await api.post("/assistant/messages", { message: text });
      setMessages((prev) => [...prev, reply]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: `error-${Date.now()}`, role: "assistant", content: `Sorry, something went wrong: ${err.message}` },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Open AI assistant"
        className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full bg-accent text-white shadow-lg hover:bg-accent/90 transition-colors flex items-center justify-center"
      >
        {open ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8-1.06 0-2.077-.163-3.02-.463L3 21l1.5-4.5C3.55 15.163 3 13.634 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-40 w-[min(380px,calc(100vw-2.5rem))] h-[min(520px,calc(100vh-9rem))] bg-surface border border-border/10 rounded-xl shadow-2xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border/10 bg-accentSoft">
            <p className="font-display text-base text-accent">AI interview assistant</p>
            <p className="text-xs text-slate">Ask about interview strategy, your resume, or your reports.</p>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-slate">
                Ask me things like "How should I answer 'tell me about yourself'?" or "What should I improve based on my last report?"
              </p>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                    m.role === "user" ? "bg-accent text-white" : "bg-canvas text-ink border border-border/10"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-canvas text-slate border border-border/10 rounded-lg px-3 py-2 text-sm">
                  Thinking…
                </div>
              </div>
            )}
          </div>

          <form onSubmit={send} className="p-3 border-t border-border/10 flex gap-2">
            <input
              className="input flex-1 text-sm"
              placeholder="Ask a question…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
            />
            <button className="btn-primary px-4 text-sm" disabled={sending || !input.trim()} type="submit">
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
