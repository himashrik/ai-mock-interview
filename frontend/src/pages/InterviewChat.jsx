import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import { ProgressBar } from "../components/ScoreBadge.jsx";
import { QuestionCard, FeedbackPanel } from "../components/InterviewWidgets.jsx";

export default function InterviewChat() {
  const { interviewId } = useParams();
  const navigate = useNavigate();

  const [interview, setInterview] = useState(null);
  const [question, setQuestion] = useState(null);
  const [answerText, setAnswerText] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [askedCount, setAskedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [finishing, setFinishing] = useState(false);

  const loadInterviewAndNext = async () => {
    setLoading(true);
    setError(null);
    try {
      const iv = await api.get(`/interviews/${interviewId}`);
      setInterview(iv);
      if (iv.status === "completed") {
        navigate(`/interview/${interviewId}/report`);
        return;
      }
      const q = await api.post(`/interviews/${interviewId}/next-question`, {});
      setQuestion(q);
      setFeedback(null);
      setAnswerText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInterviewAndNext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  const submitAnswer = async (e) => {
    e.preventDefault();
    if (!question || !answerText.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const fb = await api.post(`/interviews/${interviewId}/answers`, {
        question_id: question.id,
        text: answerText,
      });
      setFeedback(fb);
      setAskedCount((c) => c + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const nextOrFinish = async () => {
    if (interview && askedCount >= interview.num_questions) {
      setFinishing(true);
      try {
        await api.post(`/interviews/${interviewId}/complete`, {});
        navigate(`/interview/${interviewId}/report`);
      } catch (err) {
        setError(err.message);
      } finally {
        setFinishing(false);
      }
      return;
    }
    setQuestion(null);
    setFeedback(null);
    await loadInterviewAndNext();
  };

  if (loading) return <div className="p-10 text-center text-slate">Loading your interview…</div>;
  if (error && !question) return <div className="p-10 text-center text-red-600">{error}</div>;

  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-6">
      {interview && <ProgressBar current={askedCount} total={interview.num_questions} />}

      {question && <QuestionCard question={question} />}

      {!feedback ? (
        <form onSubmit={submitAnswer} className="card space-y-3">
          <label className="label">Your answer</label>
          <textarea
            className="input min-h-[160px]"
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            placeholder="Type your answer as you would say it out loud…"
            required
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn-primary" disabled={submitting} type="submit">
            {submitting ? "Evaluating…" : "Submit answer"}
          </button>
        </form>
      ) : (
        <>
          <FeedbackPanel feedback={feedback} />
          <button className="btn-primary w-full" disabled={finishing} onClick={nextOrFinish}>
            {finishing
              ? "Generating your report…"
              : askedCount >= (interview?.num_questions || 0)
              ? "Finish interview & see report"
              : "Next question"}
          </button>
        </>
      )}
    </div>
  );
}
