import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";

export default function PerformanceHistory() {
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get("/me/performance-history").then(setHistory).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl mb-6">Performance history</h1>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!error && history.length === 0 && <p className="text-slate text-sm">No completed interviews yet.</p>}

      <div className="space-y-3">
        {history.map((h) => (
          <Link key={h.interview_id} to={`/interview/${h.interview_id}/report`} className="card flex items-center justify-between hover:border-accent/40 transition-colors">
            <div>
              <p className="font-medium">{h.target_role}</p>
              <p className="text-xs text-slate capitalize">
                {h.type} · {h.completed_at ? new Date(h.completed_at).toLocaleString() : ""}
              </p>
            </div>
            <ScoreBadge score={h.overall_score} />
          </Link>
        ))}
      </div>
    </div>
  );
}
