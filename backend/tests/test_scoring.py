from app.services.scoring import (
    WEIGHTS,
    aggregate_category_scores,
    overall_score,
    question_score,
    suggest_next_difficulty,
)


def test_weights_sum_to_one_for_every_category():
    for category, weights in WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, f"{category} weights do not sum to 1.0"


def test_question_score_technical_weighs_technical_accuracy_heavily():
    sub_scores = {
        "correctness": 100, "relevance": 100, "technical_accuracy": 0,
        "completeness": 100, "communication": 100,
    }
    score = question_score("technical", sub_scores)
    # technical_accuracy has weight 0.30 in the technical rubric; zeroing it must pull the score below 100.
    assert score < 100
    assert score == round(100 * 0.35 + 0 * 0.30 + 100 * 0.15 + 100 * 0.10 + 100 * 0.10, 2)


def test_question_score_hr_ignores_technical_accuracy():
    sub_scores_a = {
        "correctness": 80, "relevance": 80, "technical_accuracy": 0,
        "completeness": 80, "communication": 80,
    }
    sub_scores_b = {**sub_scores_a, "technical_accuracy": 100}
    # HR weight for technical_accuracy is 0, so changing it must not change the score.
    assert question_score("hr", sub_scores_a) == question_score("hr", sub_scores_b)


def test_question_score_unknown_category_falls_back_to_mixed():
    sub_scores = {
        "correctness": 60, "relevance": 60, "technical_accuracy": 60,
        "completeness": 60, "communication": 60,
    }
    # All dims equal -> weighted average equals that value regardless of weights, for both categories.
    assert question_score("some_unrecognized_category", sub_scores) == question_score("mixed", sub_scores)


def test_aggregate_category_scores_averages_and_skips_empty():
    result = aggregate_category_scores({"technical": [80, 60], "hr": [], "aptitude": [100]})
    assert result == {"technical": 70.0, "aptitude": 100.0}
    assert "hr" not in result


def test_overall_score_empty_is_zero():
    assert overall_score([]) == 0.0


def test_overall_score_is_plain_mean_not_category_mean():
    # 5 technical questions (avg 90) + 1 HR question (avg 50) should NOT average to 70
    # (that would be averaging category means); it should be the mean of all 6 scores.
    scores = [90, 90, 90, 90, 90, 50]
    assert overall_score(scores) == round(sum(scores) / len(scores), 2)


def test_suggest_next_difficulty_escalates_on_high_score():
    assert suggest_next_difficulty("easy", 85) == "medium"
    assert suggest_next_difficulty("medium", 90) == "hard"
    assert suggest_next_difficulty("hard", 95) == "hard"  # already at ceiling


def test_suggest_next_difficulty_de_escalates_on_low_score():
    assert suggest_next_difficulty("hard", 30) == "medium"
    assert suggest_next_difficulty("medium", 20) == "easy"
    assert suggest_next_difficulty("easy", 10) == "easy"  # already at floor


def test_suggest_next_difficulty_holds_steady_in_middle_band():
    assert suggest_next_difficulty("medium", 65) == "medium"
