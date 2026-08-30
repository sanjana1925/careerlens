"""Explainable resume <-> job match scoring."""

from dataclasses import dataclass

from app.services import vector_store
from app.utils.skills import extract_skills, score_skills


@dataclass
class MatchResult:
    job_id: int
    match_score: float
    matched_skills: set[str]
    missing_skills: set[str]
    # Secondary signal from the Chroma/LangChain semantic layer (0-100, higher
    # = more similar), kept separate from match_score rather than blended into
    # it — match_score stays keyword-explainable ("matched: X, missing: Y");
    # this catches related skills phrased differently or outside
    # app/utils/skills.py's fixed vocabulary. None means no signal was
    # available (job not indexed yet, or GEMINI_API_KEY isn't set) — not 0.
    semantic_score: float | None = None


def match_resume_to_job(job_id: int, resume_text: str, job_description: str) -> MatchResult:
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description)
    result = score_skills(resume_skills, job_skills)

    return MatchResult(job_id=job_id, match_score=result.score, matched_skills=result.matched, missing_skills=result.missing)


def rank_jobs(resume_text: str, jobs: list[tuple[int, str]]) -> list[MatchResult]:
    """jobs: list of (job_id, job_description). Returns results sorted best-match first."""
    results = [match_resume_to_job(job_id, resume_text, description) for job_id, description in jobs]

    semantic = vector_store.semantic_scores(resume_text, [job_id for job_id, _ in jobs])
    for result in results:
        result.semantic_score = semantic.get(result.job_id)

    return sorted(results, key=lambda r: r.match_score, reverse=True)
