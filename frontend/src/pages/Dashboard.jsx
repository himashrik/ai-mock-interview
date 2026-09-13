import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { ScoreBadge } from "../components/ScoreBadge.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/me/performance-history")
      .then(setHistory)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const overallAvg =
    history.length > 0
      ? Math.round(history.reduce((sum, h) => sum + (h.overall_score || 0), 0) / history.length)
      : null;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl mb-1">Welcome, {user?.full_name || user?.email}</h1>
      <p className="text-slate mb-8">Here's where you left off.</p>

      <div className="grid md:grid-cols-3 gap-5 mb-8">
        <Link to="/resume" className="card hover:border-accent/40 transition-colors">
          <h3 className="font-medium mb-1">Resume</h3>
          <p className="text-sm text-slate">Upload or update your resume for personalized interviews.</p>
        </Link>
        <Link to="/job-description" className="card hover:border-accent/40 transition-colors">
          <h3 className="font-medium mb-1">Job description</h3>
          <p className="text-sm text-slate">Add a JD to tailor questions and get an ATS score.</p>
        </Link>
        <Link to="/interview/setup" className="card hover:border-accent/40 transition-colors">
          <h3 className="font-medium mb-1">Start an interview</h3>
          <p className="text-sm text-slate">Configure a new mock interview session.</p>
        </Link>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display text-xl">Performance history</h2>
          {overallAvg !== null && (
            <div className="flex items-center gap-2 text-sm text-slate">
              Overall average <ScoreBadge score={overallAvg} />
            </div>
          )}
        </div>

        {loading && <p className="text-sm text-slate">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && history.length === 0 && (
          <p className="text-sm text-slate">
            No completed interviews yet. <Link to="/interview/setup" className="text-accent">Start your first one</Link>.
          </p>
        )}

        <div className="divide-y divide-ink/5">
          {history.map((h) => (
            <Link
              key={h.interview_id}
              to={`/interview/${h.interview_id}/report`}
              className="flex items-center justify-between py-3 hover:bg-ink/[.02] -mx-2 px-2 rounded"
            >
              <div>
                <p className="text-sm font-medium">{h.target_role}</p>
                <p className="text-xs text-slate">
                  {h.type} · {h.completed_at ? new Date(h.completed_at).toLocaleDateString() : ""}
                </p>
              </div>
              <ScoreBadge score={h.overall_score} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
