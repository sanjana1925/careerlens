from app.utils.skills import extract_skills, score_skills, skill_category


def test_extract_skills_matches_canonical_terms():
    text = "Built services with Python, FastAPI, and PostgreSQL."
    skills = extract_skills(text)
    assert {"python", "fastapi", "postgresql"} <= skills


def test_extract_skills_resolves_aliases_to_canonical_name():
    text = "Experience with k8s, js, and nextjs deployments on GCP."
    skills = extract_skills(text)
    assert "kubernetes" in skills
    assert "javascript" in skills
    assert "next.js" in skills
    assert "gcp" in skills
    # aliases themselves are never returned, only canonical names
    assert "k8s" not in skills
    assert "js" not in skills


def test_extract_skills_respects_word_boundaries():
    # "go" and "r" are real skills but must not false-positive inside other words.
    text = "Backend developer using an algorithm for gorilla-based data goggles."
    skills = extract_skills(text)
    assert "go" not in skills
    assert "r" not in skills


def test_extract_skills_empty_text_returns_empty_set():
    assert extract_skills("") == set()


def test_skill_category_known_and_unknown():
    assert skill_category("python") == "languages"
    assert skill_category("react") == "frontend"
    assert skill_category("not-a-real-skill") is None


def test_score_skills_computes_matched_missing_and_percentage():
    result = score_skills({"python", "docker", "react"}, {"python", "docker", "kubernetes"})
    assert result.matched == {"python", "docker"}
    assert result.missing == {"kubernetes"}
    assert result.score == round(100 * 2 / 3, 1)


def test_score_skills_empty_target_yields_zero_score():
    result = score_skills({"python"}, set())
    assert result.score == 0.0
    assert result.matched == set()
    assert result.missing == set()


def test_extract_skills_covers_expanded_vocabulary():
    text = "Used Pinecone and LlamaIndex for RAG, deployed via Vercel, tracked with Sentry."
    skills = extract_skills(text)
    assert {"pinecone", "llamaindex", "rag", "vercel", "sentry"} <= skills


def test_score_skills_full_match_is_hundred():
    result = score_skills({"python", "docker"}, {"python", "docker"})
    assert result.score == 100.0
