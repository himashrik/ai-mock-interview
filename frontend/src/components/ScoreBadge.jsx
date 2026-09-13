import React from "react";

export function ScoreBadge({ score, size = "md" }) {
  const value = Math.round(score ?? 0);
  const tone =
    value >= 75 ? "bg-accentSoft text-accent" : value >= 50 ? "bg-gold/15 text-gold" : "bg-red-500/10 text-red-600 dark:text-red-400";
  const sizing = size === "lg" ? "text-2xl px-4 py-2" : "text-sm px-2.5 py-1";

  return (
    <span className={`inline-flex items-center rounded-md font-semibold ${tone} ${sizing}`}>
      {value}/100
    </span>
  );
}

export function ProgressBar({ current, total }) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs text-slate mb-1">
        <span>Question {Math.min(current + 1, total)} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-ink/5 overflow-hidden">
        <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
