from app.services import ats_scorer


def test_score_resume_without_job_description_uses_resume_category_vocabulary():
    resume = "Built a REST API in Python using FastAPI and PostgreSQL, deployed with Docker."
    result = ats_scorer.score_resume(resume)

    assert "python" in result.matched_keywords
    assert "fastapi" in result.matched_keywords
    assert 0.0 <= result.ats_score <= 100.0
    assert result.ats_score == result.skill_match_pct
    # Heuristic (no GEMINI_API_KEY in test env) narrative text is non-empty.
    assert result.strengths
    assert result.weaknesses
    assert result.missing_strengths
    assert result.suggestions


def test_score_resume_against_job_description_scores_relative_to_that_job():
    resume = "Experience with Python and Docker."
    job = "Looking for a candidate skilled in Python, Docker, Kubernetes, and AWS."

    result = ats_scorer.score_resume(resume, job)

    assert result.matched_keywords == {"python", "docker"}
    assert result.missing_keywords == {"kubernetes", "aws"}
    assert result.ats_score == round(100 * 2 / 4, 1)


def test_score_resume_no_keyword_gaps_reports_no_major_gaps():
    resume = "Python and Docker expert."
    job = "Needs Python and Docker."

    result = ats_scorer.score_resume(resume, job)

    assert result.missing_keywords == set()
    assert "No major keyword gaps" in result.weaknesses


def test_score_resume_detects_metrics_and_action_verbs():
    resume = "Led a team and reduced latency by 40% while improving throughput for 10k users."
    result = ats_scorer.score_resume(resume)

    assert "quantified outcome" in result.strengths


def test_score_resume_flags_missing_metrics_and_weak_verbs():
    resume = "Responsible for the website. Worked on some things."
    result = ats_scorer.score_resume(resume)

    assert "No quantified impact" in result.missing_strengths
    assert "Few strong action verbs" in result.missing_strengths
