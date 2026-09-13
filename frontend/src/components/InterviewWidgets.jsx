import React from "react";
import { ScoreBadge } from "./ScoreBadge.jsx";

export function QuestionCard({ question }) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3 text-xs uppercase tracking-wide text-slate">
        <span className="bg-ink/5 px-2 py-0.5 rounded">{question.category}</span>
        <span className="bg-ink/5 px-2 py-0.5 rounded">{question.difficulty}</span>
        {question.source === "resume" && (
          <span className="bg-accentSoft text-accent px-2 py-0.5 rounded">from your resume</span>
        )}
        {question.source === "jd" && (
          <span className="bg-accentSoft text-accent px-2 py-0.5 rounded">from the job description</span>
        )}
      </div>
      <p className="font-display text-lg leading-snug text-ink">{question.text}</p>
    </div>
  );
}

export function FeedbackPanel({ feedback }) {
  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg">Feedback on your answer</h3>
        <ScoreBadge score={feedback.score} size="lg" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center text-xs">
        {[
          ["Correctness", feedback.correctness],
          ["Relevance", feedback.relevance],
          ["Technical", feedback.technical_accuracy],
          ["Completeness", feedback.completeness],
          ["Communication", feedback.communication],
        ].map(([label, val]) => (
          <div key={label} className="bg-ink/5 rounded-md py-2">
            <div className="font-semibold text-ink">{Math.round(val)}</div>
            <div className="text-slate">{label}</div>
          </div>
        ))}
      </div>

      {feedback.strengths?.length > 0 && (
        <div>
          <p className="text-sm font-medium text-accent mb-1">What went well</p>
          <ul className="list-disc list-inside text-sm text-slate space-y-0.5">
            {feedback.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {feedback.weaknesses?.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gold mb-1">What was missing</p>
          <ul className="list-disc list-inside text-sm text-slate space-y-0.5">
            {feedback.weaknesses.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {feedback.suggestions?.length > 0 && (
        <div>
          <p className="text-sm font-medium text-ink mb-1">Suggestions</p>
          <ul className="list-disc list-inside text-sm text-slate space-y-0.5">
            {feedback.suggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {feedback.sample_answer && (
        <div>
          <p className="text-sm font-medium text-ink mb-1">A stronger version might sound like</p>
          <p className="text-sm text-slate bg-ink/5 rounded-md p-3">{feedback.sample_answer}</p>
        </div>
      )}
    </div>
  );
}
