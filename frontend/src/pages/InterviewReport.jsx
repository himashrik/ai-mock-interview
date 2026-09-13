import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";

export default function InterviewReport() {
  const { interviewId } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`/interviews/${interviewId}/report`).then(setReport).catch((e) => setError(e.message));
  }, [interviewId]);

  if (error) return <div className="p-10 text-center text-red-600">{error}</div>;
  if (!report) return <div className="p-10 text-center text-slate">Loading report…</div>;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-6">
      <div className="card flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl mb-1">Your interview report</h1>
          <p className="text-slate text-sm">Suggested next difficulty: <strong className="text-ink">{report.next_difficulty}</strong></p>
        </div>
        <ScoreBadge score={report.overall_score} size="lg" />
      </div>

      {Object.keys(report.category_scores).length > 0 && (
        <div className="card">
          <h2 className="font-display text-lg mb-3">Category scores</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
            {Object.entries(report.category_scores).map(([cat, score]) => (
              <div key={cat} className="bg-ink/5 rounded-md py-3">
                <div className="font-semibold">{Math.round(score)}</div>
                <div className="text-slate text-xs capitalize">{cat}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-5">
        <ReportSection title="Strongest areas" items={report.strongest_areas} tone="text-accent" />
        <ReportSection title="Weakest areas" items={report.weakest_areas} tone="text-gold" />
      </div>

      <ReportSection title="Common mistakes" items={report.common_mistakes} />
      <ReportSection title="Study plan" items={report.study_plan} />
      <ReportSection title="Tips" items={report.tips} />

      {report.resume_alignment_notes && (
        <div className="card">
          <h2 className="font-display text-lg mb-2">Resume/JD alignment</h2>
          <p className="text-sm text-slate">{report.resume_alignment_notes}</p>
        </div>
      )}
    </div>
  );
}

function ReportSection({ title, items, tone = "text-ink" }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="card">
      <h2 className={`font-display text-lg mb-2 ${tone}`}>{title}</h2>
      <ul className="list-disc list-inside text-sm text-slate space-y-1">
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  );
}
