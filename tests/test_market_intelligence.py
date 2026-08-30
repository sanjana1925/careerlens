from app.services import market_intelligence


def test_analyze_market_empty_postings_returns_empty():
    demand, gaps = market_intelligence.analyze_market([])
    assert demand == []
    assert gaps == []


def test_analyze_market_ranks_skills_by_demand_percentage():
    postings = [
        "Needs Python and Docker.",
        "Needs Python and Kubernetes.",
        "Needs Python only.",
    ]

    demand, _ = market_intelligence.analyze_market(postings)

    by_skill = {d.skill: d for d in demand}
    assert by_skill["python"].percentage == 100.0
    assert by_skill["python"].job_count == 3
    assert by_skill["docker"].job_count == 1
    assert demand[0].skill == "python"  # highest-demand skill sorts first


def test_analyze_market_computes_skill_gaps_against_resume():
    postings = ["Needs Python and Kubernetes.", "Needs Python and Docker."]
    resume_text = "Experienced Python developer."

    demand, gaps = market_intelligence.analyze_market(postings, resume_text)

    assert "python" not in gaps  # resume already has it
    assert "kubernetes" in gaps
    assert "docker" in gaps


def test_analyze_market_no_resume_yields_no_gaps():
    demand, gaps = market_intelligence.analyze_market(["Needs Python."], resume_text="")
    assert gaps == []
