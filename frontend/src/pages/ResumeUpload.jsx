import React, { useState } from "react";
import FileDropzone from "../components/FileDropzone.jsx";
import { api } from "../api/client.js";

export default function ResumeUpload() {
  const [document, setDocument] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFile = async (file) => {
    setUploading(true);
    setError(null);
    setAnalysis(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const doc = await api.postForm("/resumes", form);
      setDocument(doc);
      if (doc.status === "ready") {
        const a = await api.get(`/resumes/${doc.id}/analysis`);
        setAnalysis(a);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="font-display text-3xl mb-1">Your resume</h1>
      <p className="text-slate mb-8">Upload a PDF or DOCX. We'll extract and index it for personalized questions.</p>

      <FileDropzone accept=".pdf,.docx" onFile={handleFile} label="Upload your resume" />

      {uploading && <p className="text-sm text-slate mt-4">Processing your resume…</p>}
      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

      {document && document.status === "failed" && (
        <p className="text-sm text-red-600 mt-4">{document.error_message}</p>
      )}

      {document && document.status === "ready" && (
        <div className="mt-6 card">
          <p className="text-sm text-accent font-medium mb-4">✓ {document.filename} indexed and ready</p>

          {!analysis && <p className="text-sm text-slate">Analyzing…</p>}

          {analysis && (
            <div className="space-y-4 text-sm">
              <AnalysisSection title="Skills" items={analysis.skills} />
              <AnalysisSection title="Experience" items={analysis.experience} />
              <AnalysisSection title="Projects" items={analysis.projects} />
              <AnalysisSection title="Education" items={analysis.education} />
              <AnalysisSection title="Certifications" items={analysis.certifications} />
              <AnalysisSection title="Achievements" items={analysis.achievements} />
              <AnalysisSection title="Missing information" items={analysis.missing_information} tone="text-gold" />
              <AnalysisSection title="Potential interview topics" items={analysis.potential_interview_topics} tone="text-accent" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AnalysisSection({ title, items, tone = "text-ink" }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className={`font-medium mb-1 ${tone}`}>{title}</p>
      <ul className="list-disc list-inside text-slate space-y-0.5">
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  );
}
