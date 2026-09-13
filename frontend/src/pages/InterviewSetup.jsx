import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

const TYPES = [
  ["hr", "HR"],
  ["technical", "Technical"],
  ["aptitude", "Aptitude"],
  ["behavioral", "Behavioral"],
  ["gd", "Group Discussion"],
  ["mixed", "Mixed"],
];
const LEVELS = [["fresher", "Fresher"], ["junior", "Junior"], ["mid", "Mid-level"], ["senior", "Senior"]];
const DIFFICULTIES = [["easy", "Easy"], ["medium", "Medium"], ["hard", "Hard"]];

export default function InterviewSetup() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState([]);
  const [jds, setJds] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const [form, setForm] = useState({
    type: "technical",
    target_role: "",
    experience_level: "junior",
    difficulty: "medium",
    mode: "general",
    num_questions: 8,
    resume_id: "",
    jd_id: "",
  });

  useEffect(() => {
    api.get("/resumes").then((docs) => setResumes(docs.filter((d) => d.status === "ready"))).catch(() => {});
    api.get("/job-descriptions").then((docs) => setJds(docs.filter((d) => d.status === "ready"))).catch(() => {});
  }, []);

  const update = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const payload = { ...form, resume_id: form.resume_id || null, jd_id: form.jd_id || null };
      const interview = await api.post("/interviews", payload);
      navigate(`/interview/${interview.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl mb-1">Set up your interview</h1>
      <p className="text-slate mb-8">Configure the session and we'll generate grounded questions as you go.</p>

      <form onSubmit={handleSubmit} className="card space-y-5">
        <div>
          <label className="label">Interview type</label>
          <div className="grid grid-cols-3 gap-2">
            {TYPES.map(([val, label]) => (
              <button
                type="button" key={val}
                className={`text-sm px-3 py-2 rounded-md border ${form.type === val ? "bg-accent text-white border-accent" : "border-border/15"}`}
                onClick={() => update("type", val)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">Target role</label>
          <input className="input" required value={form.target_role} onChange={(e) => update("target_role", e.target.value)} placeholder="e.g. Backend Engineer" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Experience level</label>
            <select className="input" value={form.experience_level} onChange={(e) => update("experience_level", e.target.value)}>
              {LEVELS.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Difficulty</label>
            <select className="input" value={form.difficulty} onChange={(e) => update("difficulty", e.target.value)}>
              {DIFFICULTIES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="label">Number of questions: {form.num_questions}</label>
          <input
            type="range" min={3} max={20} value={form.num_questions}
            onChange={(e) => update("num_questions", Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="label">Mode</label>
          <div className="flex gap-2">
            <button type="button" className={`text-sm px-3 py-2 rounded-md border flex-1 ${form.mode === "general" ? "bg-accent text-white border-accent" : "border-border/15"}`} onClick={() => update("mode", "general")}>
              General
            </button>
            <button type="button" className={`text-sm px-3 py-2 rounded-md border flex-1 ${form.mode === "resume" ? "bg-accent text-white border-accent" : "border-border/15"}`} onClick={() => update("mode", "resume")}>
              Resume-based
            </button>
          </div>
        </div>

        {form.mode === "resume" && (
          <>
            <div>
              <label className="label">Resume</label>
              <select className="input" required={form.mode === "resume"} value={form.resume_id} onChange={(e) => update("resume_id", e.target.value)}>
                <option value="">Select a resume…</option>
                {resumes.map((r) => <option key={r.id} value={r.id}>{r.filename}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Job description (optional)</label>
              <select className="input" value={form.jd_id} onChange={(e) => update("jd_id", e.target.value)}>
                <option value="">None</option>
                {jds.map((j) => <option key={j.id} value={j.id}>{j.filename}</option>)}
              </select>
            </div>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button className="btn-primary w-full" disabled={busy} type="submit">
          {busy ? "Creating…" : "Start interview"}
        </button>
      </form>
    </div>
  );
}
