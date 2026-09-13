"""A rule-based, zero-dependency stand-in for a real LLM provider.

This exists so the whole application -- resume analysis, ATS scoring, the adaptive interview
loop, the AI assistant chat -- actually runs end to end with no API key configured at all, for
anyone evaluating the project (a recruiter, an interviewer, you on a plane with no internet).

Honesty matters here: this is template/rule-based content, not real AI-generated feedback, and it
says so wherever a human will read it (feedback text, tips, the assistant's chat replies). It never
silently pretends to be a genuine model response. `get_llm_provider()` in `factory.py` only falls
back to this when no real provider is configured/reachable, and logs a warning when it does.
"""
import hashlib
import json
import re

from app.llm.base import LLMProvider

DEMO_NOTICE = (
    "[Demo mode: no LLM API key configured, so this is template content rather than real "
    "AI-generated feedback. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env for the real thing.]"
)

QUESTION_BANK = {
    "hr": [
        "Tell me about yourself and what draws you to this role.",
        "What would you say is your biggest professional weakness, and what are you doing about it?",
        "Describe a time you had a disagreement with a manager. How did you handle it?",
    ],
    "technical": [
        "Walk me through a project you're proud of, including a technical trade-off you had to make.",
        "How would you design a system to handle a sudden 10x spike in traffic?",
        "Explain how you would debug a service that's intermittently returning errors in production.",
    ],
    "aptitude": [
        "A train travels 60 km in 45 minutes. At the same speed, how long will it take to travel 100 km?",
        "If a task takes 3 people 8 days, how many days would it take 4 people, assuming constant effort per person?",
        "You have two ropes that each take exactly 1 hour to burn, but burn unevenly. How do you measure 45 minutes?",
    ],
    "behavioral": [
        "Tell me about a time you missed a deadline. What happened, and what did you learn?",
        "Describe a situation where you had to influence someone without formal authority.",
        "Tell me about a time you received difficult feedback. How did you respond?",
    ],
    "gd": [
        "Should companies allow fully remote work for all engineering roles? State and defend a position.",
        "Is it better to be a generalist or a specialist early in your career? Argue a side.",
    ],
}

CATEGORY_PATTERN = re.compile(r"conducting an? ([a-z]+) interview", re.IGNORECASE)


def _pick(seq: list, seed_text: str):
    """Deterministic-but-varied pick based on a hash of the input, so repeated demo calls don't
    always return the exact same line, without needing real randomness."""
    idx = int(hashlib.sha256(seed_text.encode()).hexdigest(), 16) % len(seq)
    return seq[idx]


def _extract_category(system_prompt: str) -> str:
    match = CATEGORY_PATTERN.search(system_prompt)
    return match.group(1).lower() if match else "hr"


def _extract_between(text: str, start_marker: str, end_marker: str) -> str:
    try:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker, start)
        return text[start:end].strip()
    except ValueError:
        return ""


class MockLLMProvider(LLMProvider):
    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500) -> str:
        if "AI interviewer conducting" in system_prompt:
            return json.dumps(self._mock_question(system_prompt, user_prompt))
        if "interview answer evaluator" in system_prompt:
            return json.dumps(self._mock_evaluation(user_prompt))
        if "resume analysis engine" in system_prompt:
            return json.dumps(self._mock_resume_analysis())
        if "job-description analysis engine" in system_prompt:
            return json.dumps(self._mock_jd_analysis())
        if "ATS (Applicant Tracking System)" in system_prompt:
            return json.dumps(self._mock_ats_analysis())
        if "narrative sections" in system_prompt:
            return json.dumps(self._mock_narrative())
        return "{}"

    def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> str:
        # Used by the AI assistant chat.
        message = _extract_between(user_prompt, "User's new message:", "Respond as the assistant.")
        lowered = message.lower()

        if "star" in lowered:
            tip = (
                "The STAR method: Situation (brief context), Task (what you needed to do), "
                "Action (what YOU specifically did), Result (the measurable outcome). Most people "
                "under-invest in the Result -- try to end with a number or concrete outcome."
            )
        elif "resume" in lowered:
            tip = (
                "For resume feedback, use the ATS analysis page against a specific job description -- "
                "it'll give you a real score plus matching/missing keywords, which is more useful than "
                "generic resume advice."
            )
        elif "weakness" in lowered:
            tip = (
                "For 'what's your weakness', pick something real but not core to the role, show "
                "self-awareness, and describe a concrete step you're taking about it -- avoid the "
                "cliche 'I work too hard' answer."
            )
        else:
            tip = (
                "Try to be specific rather than general in your answers -- concrete examples with a "
                "measurable outcome consistently score better than descriptions of general approach."
            )

        return f"{DEMO_NOTICE}\n\n{tip}"

    def _mock_question(self, system_prompt: str, user_prompt: str) -> dict:
        category = _extract_category(system_prompt)
        bank = QUESTION_BANK.get(category, QUESTION_BANK["hr"])
        question = _pick(bank, user_prompt)
        return {
            "question": question,
            "category": category,
            "difficulty": "medium",
            "source": "general",
            "grounded_on": "demo mode -- not actually grounded in your documents",
        }

    def _mock_evaluation(self, user_prompt: str) -> dict:
        answer = _extract_between(user_prompt, "Candidate's answer:", "Grounding context")
        # Deterministic-but-varied score so a demo run still feels like it's responding to content,
        # without claiming to have actually evaluated correctness (it hasn't -- it's template scoring).
        base = 55 + (int(hashlib.sha256(answer.encode()).hexdigest(), 16) % 35) if answer else 60
        return {
            "correctness": base,
            "relevance": base,
            "technical_accuracy": base,
            "completeness": base,
            "communication": base,
            "strengths": ["You provided a direct, on-topic answer."],
            "weaknesses": [DEMO_NOTICE],
            "suggestions": ["Add a specific, measurable example to strengthen this answer."],
            "sample_answer": DEMO_NOTICE,
        }

    def _mock_resume_analysis(self) -> dict:
        return {
            "skills": [], "education": [], "experience": [], "projects": [], "certifications": [],
            "achievements": [], "missing_information": [DEMO_NOTICE],
            "potential_interview_topics": ["Connect a real API key to get topics grounded in your actual resume."],
        }

    def _mock_jd_analysis(self) -> dict:
        return {
            "target_role": DEMO_NOTICE, "required_skills": [], "preferred_skills": [],
            "experience_requirement": "", "responsibilities": [], "technologies": [],
            "important_keywords": [], "expected_competencies": [],
        }

    def _mock_ats_analysis(self) -> dict:
        return {
            "score": 50, "matching_keywords": [], "missing_keywords": [],
            "strengths": [DEMO_NOTICE], "weaknesses": [],
            "suggestions": ["Connect a real API key for an accurate, evidence-based ATS score."],
        }

    def _mock_narrative(self) -> dict:
        return {
            "strongest_areas": [], "weakest_areas": [], "common_mistakes": [],
            "study_plan": [DEMO_NOTICE], "tips": ["Practice answering out loud, not just in your head."],
            "resume_alignment_notes": DEMO_NOTICE,
        }
