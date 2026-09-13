import React, { useEffect, useState } from "react";
import FileDropzone from "../components/FileDropzone.jsx";
import { api } from "../api/client.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";

export default function JobDescription() {
  const [mode, setMode] = useState("paste"); // "paste" | "upload"
  const [text, setText] = useState("");
  const [jdDoc, setJdDoc] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [atsReport, setAtsReport] = useState(null);

  useEffect(() => {
    api.get("/resumes").then(setResumes).catch(() => {});
  }, []);

  const submitJdText = async () => {
    setBusy(true);
    setError(null);
    try {
      const doc = await api.post("/job-descriptions/text", { text, title: "Pasted Job Description" });
      setJdDoc(doc);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const submitJdFile = async (file) => {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const doc = await api.postForm("/job-descriptions/upload", form);
      setJdDoc(doc);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const runAts = async () => {
    if (!jdDoc || !selectedResumeId) return;
    setBusy(true);
    setError(null);
    setAtsReport(null);
    try {
      const report = await api.post("/ats/analyze", { resume_id: selectedResumeId, jd_id: jdDoc.id });
      setAtsReport(report);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl mb-1">Job description</h1>
      <p className="text-slate mb-8">Paste or upload a JD to personalize your interview and get an ATS score.</p>

      <div className="flex gap-2 mb-4 text-sm">
        <button
          className={`px-3 py-1.5 rounded-md ${mode === "paste" ? "bg-accent text-white" : "bg-ink/5"}`}
          onClick={() => setMode("paste")}
        >
          Paste text
        </button>
        <button
          className={`px-3 py-1.5 rounded-md ${mode === "upload" ? "bg-accent text-white" : "bg-ink/5"}`}
          onClick={() => setMode("upload")}
        >
          Upload file
        </button>
      </div>

      {mode === "paste" ? (
        <div>
          <textarea
            className="input min-h-[180px]"
            placeholder="Paste the job description here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button className="btn-primary mt-3" disabled={busy || !text.trim()} onClick={submitJdText}>
            {busy ? "Processing…" : "Save job description"}
          </button>
        </div>
      ) : (
        <FileDropzone accept=".pdf,.docx" onFile={submitJdFile} label="Upload the job description" />
      )}

      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

      {jdDoc && jdDoc.status === "ready" && (
        <div className="card mt-6">
          <p className="text-sm text-accent font-medium mb-4">✓ Job description indexed and ready</p>

          <label className="label">Resume to compare against</label>
          <select
            className="input mb-3"
            value={selectedResumeId}
            onChange={(e) => setSelectedResumeId(e.target.value)}
          >
            <option value="">Select a resume…</option>
            {resumes.filter((r) => r.status === "ready").map((r) => (
              <option key={r.id} value={r.id}>{r.filename}</option>
            ))}
          </select>
          {resumes.length === 0 && (
            <p className="text-xs text-slate mb-3">
              No resumes uploaded yet — <a href="/resume" className="text-accent">upload one first</a>.
            </p>
          )}
          <button className="btn-primary" disabled={busy || !selectedResumeId} onClick={runAts}>
            {busy ? "Analyzing…" : "Run ATS analysis"}
          </button>
        </div>
      )}

      {atsReport && (
        <div className="card mt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display text-xl">ATS score</h2>
            <ScoreBadge score={atsReport.score} size="lg" />
          </div>
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-accent mb-1">Matching keywords</p>
              <p className="text-slate">{atsReport.matching_keywords.join(", ") || "—"}</p>
            </div>
            <div>
              <p className="font-medium text-gold mb-1">Missing keywords</p>
              <p className="text-slate">{atsReport.missing_keywords.join(", ") || "—"}</p>
            </div>
            <div>
              <p className="font-medium mb-1">Strengths</p>
              <ul className="list-disc list-inside text-slate">
                {atsReport.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">Weaknesses</p>
              <ul className="list-disc list-inside text-slate">
                {atsReport.weaknesses.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </div>
          {atsReport.suggestions.length > 0 && (
            <div className="mt-4 text-sm">
              <p className="font-medium mb-1">Suggestions</p>
              <ul className="list-disc list-inside text-slate">
                {atsReport.suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
