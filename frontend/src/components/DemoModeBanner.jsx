import React, { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function DemoModeBanner() {
  const [demoMode, setDemoMode] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api
      .get("/system/status")
      .then((status) => setDemoMode(status.demo_mode))
      .catch(() => {});
  }, []);

  if (!demoMode || dismissed) return null;

  return (
    <div className="bg-gold/10 border-b border-gold/20 px-6 py-2.5 text-sm text-ink flex items-center justify-between gap-4">
      <p>
        <strong className="text-gold">Demo mode:</strong> no LLM API key is configured on the server, so
        questions and feedback are template content rather than real AI-generated responses. Set{" "}
        <code className="bg-ink/5 px-1 rounded">ANTHROPIC_API_KEY</code> or{" "}
        <code className="bg-ink/5 px-1 rounded">OPENAI_API_KEY</code> in the backend's <code className="bg-ink/5 px-1 rounded">.env</code> for the real thing.
      </p>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="text-slate hover:text-ink flex-shrink-0"
      >
        ✕
      </button>
    </div>
  );
}
