"""All scores are computed here in plain Python — never by the LLM — so the
methodology is deterministic, testable, and can be shown to the user."""

# Weights per interview category. Must sum to 1.0.
WEIGHTS: dict[str, dict[str, float]] = {
    "technical": {
        "correctness": 0.35, "technical_accuracy": 0.30, "completeness": 0.15,
        "relevance": 0.10, "communication": 0.10,
    },
    "hr": {
        "correctness": 0.20, "technical_accuracy": 0.0, "completeness": 0.20,
        "relevance": 0.30, "communication": 0.30,
    },
    "behavioral": {
        "correctness": 0.20, "technical_accuracy": 0.0, "completeness": 0.20,
        "relevance": 0.30, "communication": 0.30,
    },
    "gd": {
        "correctness": 0.15, "technical_accuracy": 0.0, "completeness": 0.15,
        "relevance": 0.30, "communication": 0.40,
    },
    "aptitude": {
        "correctness": 0.55, "technical_accuracy": 0.0, "completeness": 0.20,
        "relevance": 0.15, "communication": 0.10,
    },
    "mixed": {  # used only if a question's own category is somehow unavailable
        "correctness": 0.30, "technical_accuracy": 0.15, "completeness": 0.20,
        "relevance": 0.20, "communication": 0.15,
    },
}


def question_score(category: str, sub_scores: dict[str, float]) -> float:
    weights = WEIGHTS.get(category, WEIGHTS["mixed"])
    total = sum(sub_scores.get(dim, 0.0) * w for dim, w in weights.items())
    return round(total, 2)


def aggregate_category_scores(question_scores_by_category: dict[str, list[float]]) -> dict[str, float]:
    return {
        cat: round(sum(scores) / len(scores), 2)
        for cat, scores in question_scores_by_category.items()
        if scores
    }


def overall_score(all_question_scores: list[float]) -> float:
    if not all_question_scores:
        return 0.0
    return round(sum(all_question_scores) / len(all_question_scores), 2)


def suggest_next_difficulty(current_difficulty: str, overall: float) -> str:
    order = ["easy", "medium", "hard"]
    idx = order.index(current_difficulty) if current_difficulty in order else 1
    if overall >= 80 and idx < 2:
        return order[idx + 1]
    if overall < 50 and idx > 0:
        return order[idx - 1]
    return current_difficulty
