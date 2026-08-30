"""ATS compatibility scoring.

The score, matched keywords, and missing keywords stay deterministic
(keyword match against `app/utils/skills.py`) — that's what makes the score
explainable and reproducible. When `GEMINI_API_KEY` is set, the strengths /
weaknesses / missing-strengths / suggestions text is upgraded to an
LLM-written explanation grounded in those same matched/missing lists;
otherwise it falls back to the templated heuristic text. Either way the
return shape (ATSResult) is the same.
"""

import re
from dataclasses import dataclass, field

from app.services import llm_client, vector_store
from app.utils.skills import SKILL_CATEGORIES, SKILL_VOCABULARY, extract_skills, score_skills, skill_category

# Resume-quality signals that go beyond keyword matching: an ATS reviewer (human
# or automated) also looks for quantified impact and ownership language, not
# just skill coverage.
ACTION_VERBS = {
    "led", "built", "designed", "developed", "implemented", "architected",
    "launched", "optimized", "reduced", "increased", "improved", "automated",
    "migrated", "scaled", "deployed", "managed", "mentored", "created",
    "spearheaded", "delivered", "engineered", "streamlined", "drove",
    "founded", "shipped",
}
_ACTION_VERB_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(ACTION_VERBS) + r")(?!\w)", re.IGNORECASE
)
_METRIC_PATTERN = re.compile(
    r"\d+(\.\d+)?\s?(%|percent|x\b|k\b|million|billion|ms\b|hours?|days?|users?|requests?|qps)",
    re.IGNORECASE,
)


@dataclass
class ATSResult:
    ats_score: float
    skill_match_pct: float
    matched_keywords: set[str] = field(default_factory=set)
    missing_keywords: set[str] = field(default_factory=set)
    strengths: str = ""
    weaknesses: str = ""
    missing_strengths: str = ""
    suggestions: str = ""


def _quality_signals(resume_text: str) -> tuple[bool, int]:
    has_metrics = bool(_METRIC_PATTERN.search(resume_text))
    action_verb_count = len(set(m.lower() for m in _ACTION_VERB_PATTERN.findall(resume_text)))
    return has_metrics, action_verb_count


def _group_by_category(skills: set[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for skill in skills:
        grouped.setdefault(skill_category(skill) or "other", []).append(skill)
    return {category: sorted(skills) for category, skills in sorted(grouped.items())}


def _missing_strengths_heuristic(missing: set[str], has_metrics: bool, action_verb_count: int) -> str:
    points = []

    if missing:
        grouped = _group_by_category(missing)
        parts = [
            f"{category.replace('_', ' ').title()} ({', '.join(skills[:6])})"
            for category, skills in grouped.items()
        ]
        points.append("In-demand skills not yet on the resume — " + "; ".join(parts) + ".")

    if not has_metrics:
        points.append(
            "No quantified impact detected (%, counts, time saved, scale) — "
            "add measurable outcomes to bullet points."
        )

    if action_verb_count < 3:
        points.append(
            "Few strong action verbs found — lead bullets with verbs like "
            "'led', 'built', 'optimized', 'reduced' instead of passive phrasing."
        )

    if not points:
        return "No major strong-point gaps detected — resume covers the expected skills and reads with concrete, quantified impact."
    return " ".join(points)


def _heuristic_narrative(
    matched: set[str], missing: set[str], has_metrics: bool, action_verb_count: int
) -> tuple[str, str, str, str]:
    strengths = f"Demonstrates {len(matched)} in-demand skills: {', '.join(sorted(matched)) or 'none detected'}."
    if has_metrics:
        strengths += " Includes at least one quantified outcome."

    weaknesses = (
        f"Missing {len(missing)} keywords relevant to the target: {', '.join(sorted(missing)[:10]) or 'none'}."
        if missing else "No major keyword gaps detected."
    )

    missing_strengths = _missing_strengths_heuristic(missing, has_metrics, action_verb_count)

    suggestions = (
        f"Consider adding evidence of: {', '.join(sorted(missing)[:5])}."
        if missing else "Resume already covers the key expected skills."
    )
    if not has_metrics:
        suggestions += " Quantify 2-3 bullet points with numbers (%, time saved, scale, users)."
    if action_verb_count < 3:
        suggestions += " Rewrite weak bullets to start with a strong action verb."

    return strengths, weaknesses, missing_strengths, suggestions


def _market_context_block(postings: list[dict]) -> str:
    if not postings:
        return ""
    listings = "\n".join(
        f"- {p['title']} at {p['company']}: {p['snippet'][:300]}" for p in postings if p.get("title")
    )
    if not listings:
        return ""
    return (
        "\n\nReal job postings currently in the market, semantically similar to this "
        f"resume/target (retrieved via a Chroma vector search — use these to ground "
        f"missing_strengths/suggestions in what employers are actually asking for, "
        f"not just the keyword list above):\n{listings}\n"
    )


def _llm_narrative(
    resume_text: str, job_description: str, matched: set[str], missing: set[str], market_context: str = ""
) -> tuple[str, str, str, str] | None:
    prompt = f"""You are an ATS (applicant tracking system) resume reviewer.

Resume text:
\"\"\"{resume_text[:6000]}\"\"\"

{"Target job description:\n\"\"\"" + job_description[:3000] + "\"\"\"" if job_description else "No specific job description was provided — evaluate against general industry expectations."}

Keyword analysis already performed (treat as ground truth, do not contradict it):
- Matched skills: {', '.join(sorted(matched)) or 'none'}
- Missing skills: {', '.join(sorted(missing)) or 'none'}
{market_context}
Write a short, specific, encouraging-but-honest review. Respond as JSON with exactly these keys:
- "strengths": 1-3 sentences on what the resume does well, citing specifics from the resume text (projects, experience, quantified impact), not just the keyword list.
- "weaknesses": 1-3 sentences on concrete gaps in how the resume is written — vague bullet points, missing metrics, weak project descriptions.
- "missing_strengths": 1-3 sentences on the specific strong points this resume is missing to be competitive for this target — combine the missing skills above with resume-quality gaps (e.g. no quantified impact, no leadership/ownership examples, no certifications relevant to the target), phrased as what to ADD rather than what's wrong.
- "suggestions": 1-3 sentences of actionable next steps to improve the resume for this target.
"""

    data = llm_client.generate_json(prompt)
    if not isinstance(data, dict):
        return None
    strengths = data.get("strengths")
    weaknesses = data.get("weaknesses")
    missing_strengths = data.get("missing_strengths")
    suggestions = data.get("suggestions")
    if not (
        isinstance(strengths, str)
        and isinstance(weaknesses, str)
        and isinstance(missing_strengths, str)
        and isinstance(suggestions, str)
    ):
        return None
    return strengths, weaknesses, missing_strengths, suggestions


def score_resume(resume_text: str, job_description: str = "") -> ATSResult:
    resume_skills = extract_skills(resume_text)

    if job_description:
        target_skills = extract_skills(job_description)
    else:
        # No specific job: compare against the categories the resume already
        # touches (e.g. backend + cloud/devops), not the entire cross-domain
        # vocabulary — nobody is expected to cover mobile, BI tooling, and
        # backend frameworks all at once, so that denominator understated
        # everyone's score. Falls back to the full vocabulary only when no
        # category can be inferred (e.g. an empty or non-technical resume).
        resume_categories = {skill_category(s) for s in resume_skills if skill_category(s)}
        target_skills = (
            {s for cat in resume_categories for s in SKILL_CATEGORIES.get(cat, [])}
            if resume_categories
            else set(SKILL_VOCABULARY)
        )

    result = score_skills(resume_skills, target_skills)
    matched, missing = result.matched, result.missing
    skill_match_pct = result.score
    ats_score = skill_match_pct

    has_metrics, action_verb_count = _quality_signals(resume_text)

    narrative = None
    if llm_client.is_available():
        market_context = ""
        if vector_store.is_available():
            postings = vector_store.similar_postings(job_description or resume_text, k=3)
            market_context = _market_context_block(postings)
        narrative = _llm_narrative(resume_text, job_description, matched, missing, market_context)
    strengths, weaknesses, missing_strengths, suggestions = narrative or _heuristic_narrative(
        matched, missing, has_metrics, action_verb_count
    )

    return ATSResult(
        ats_score=ats_score,
        skill_match_pct=skill_match_pct,
        matched_keywords=matched,
        missing_keywords=missing,
        strengths=strengths,
        weaknesses=weaknesses,
        missing_strengths=missing_strengths,
        suggestions=suggestions,
    )
