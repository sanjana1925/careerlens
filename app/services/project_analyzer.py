"""Detects repetitive / low-diversity projects in a resume.

`analyze_projects` takes already-segmented (title, description) pairs.
`extract_projects_from_resume` does that segmentation from raw resume text —
using Gemini when available (it handles arbitrary resume formatting far better
than a fixed set of section-header rules), falling back to a heuristic
"PROJECTS section, title line + following bullets" parser otherwise.

When `GEMINI_API_KEY` is set, categorization + repetition judgement + diversification
suggestions are produced by Gemini (it can spot conceptual overlap a fixed keyword
list can't, e.g. two projects that are both "toy dataset regression" under different
names). Falls back to the keyword-based heuristic below on any failure so this
never blocks the request.
"""

import re
from dataclasses import dataclass

from app.services import llm_client

# Coarse categories used to flag "same shape, different dataset" ML projects.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "supervised-ml-prediction": ["prediction", "predict", "regression", "classifier", "classification"],
    "rag": ["rag", "retrieval augmented", "vector search", "embeddings"],
    "ai-agents": ["agent", "multi-agent", "autonomous"],
    "deployment": ["deployment", "docker", "kubernetes", "ci/cd", "production"],
    "computer-vision": ["image", "cv", "opencv", "object detection", "yolo"],
    "nlp": ["nlp", "text classification", "sentiment", "language model"],
    "data-pipeline": ["etl", "pipeline", "airflow", "spark", "streaming"],
}

DIVERSIFICATION_SUGGESTIONS = {
    "supervised-ml-prediction": "Build an end-to-end RAG evaluation system, an AI agent, or a deployed real-time ML pipeline instead of another prediction/classification project.",
}


@dataclass
class ProjectFinding:
    title: str
    category: str | None
    is_repetitive: bool


def categorize(description: str) -> str | None:
    lowered = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def _heuristic_analyze(projects: list[dict]) -> tuple[list[ProjectFinding], list[str]]:
    categorized = [(p["title"], categorize(f"{p['title']} {p['description']}")) for p in projects]

    counts: dict[str, int] = {}
    for _, category in categorized:
        if category:
            counts[category] = counts.get(category, 0) + 1

    findings = [
        ProjectFinding(title=title, category=category, is_repetitive=bool(category and counts.get(category, 0) > 1))
        for title, category in categorized
    ]

    suggestions = [
        DIVERSIFICATION_SUGGESTIONS.get(category, f"Diversify beyond the '{category}' project type — {count} projects share this category.")
        for category, count in counts.items()
        if count > 1
    ]

    return findings, suggestions


def _llm_analyze(projects: list[dict]) -> tuple[list[ProjectFinding], list[str]] | None:
    listing = "\n".join(
        f"{i + 1}. Title: {p['title']}\n   Description: {p['description']}" for i, p in enumerate(projects)
    )
    prompt = f"""You review a candidate's resume projects for quality and diversity.

Projects (in order):
{listing}

For each project, assign a short kebab-case category describing its conceptual
type (e.g. "supervised-ml-prediction", "rag", "ai-agents", "computer-vision",
"deployment", "nlp", "data-pipeline", "web-app", "mobile-app", or invent a
fitting one). Two projects should share a category if they demonstrate
essentially the same skill/pattern even if the dataset or domain differs
(e.g. "house price prediction" and "student grade prediction" are both
supervised-ml-prediction).

Respond as JSON with exactly this shape:
{{
  "projects": [
    {{"title": "<title exactly as given>", "category": "<category>", "is_repetitive": <true if 2+ projects share this category>}},
    ...
  ],
  "suggestions": ["<1-2 sentence diversification suggestion for each repeated category>", ...]
}}

Return exactly {len(projects)} entries in "projects", in the same order as given above.
"""

    data = llm_client.generate_json(prompt)
    if not isinstance(data, dict):
        return None

    raw_projects = data.get("projects")
    raw_suggestions = data.get("suggestions")
    if not isinstance(raw_projects, list) or len(raw_projects) != len(projects):
        return None
    if not isinstance(raw_suggestions, list):
        return None

    try:
        findings = [
            ProjectFinding(
                title=projects[i]["title"],
                category=entry.get("category") or None,
                is_repetitive=bool(entry.get("is_repetitive")),
            )
            for i, entry in enumerate(raw_projects)
        ]
    except (AttributeError, KeyError, TypeError):
        return None

    suggestions = [s for s in raw_suggestions if isinstance(s, str)]
    return findings, suggestions


def analyze_projects(projects: list[dict]) -> tuple[list[ProjectFinding], list[str]]:
    """projects: list of {"title": str, "description": str}. Returns (findings, suggestions)."""
    if llm_client.is_available():
        result = _llm_analyze(projects)
        if result is not None:
            return result

    return _heuristic_analyze(projects)


# Section headers that introduce a resume's projects block, and the headers
# that mark the *next* section (so we know where the projects block ends).
_PROJECT_SECTION_HEADERS = {
    "projects", "personal projects", "academic projects", "project experience",
    "key projects", "selected projects", "side projects",
}
_OTHER_SECTION_HEADERS = {
    "experience", "work experience", "professional experience", "employment history",
    "education", "skills", "technical skills", "certifications", "achievements",
    "publications", "awards", "summary", "objective", "contact", "references",
    "leadership", "extracurricular", "volunteering",
}
_BULLET_PREFIXES = ("•", "-", "*", "▪", "‣", "◦", "·")


def _heuristic_segment(resume_text: str) -> list[dict]:
    lines = resume_text.splitlines()

    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        normalized = line.strip().lower().rstrip(":")
        if start is None and normalized in _PROJECT_SECTION_HEADERS:
            start = i + 1
            continue
        if start is not None and normalized in _OTHER_SECTION_HEADERS:
            end = i
            break

    if start is None:
        return []

    projects: list[dict] = []
    current_title: str | None = None
    current_desc: list[str] = []

    def flush() -> None:
        if current_title:
            description = " ".join(d.strip(" \t").lstrip("".join(_BULLET_PREFIXES)).strip() for d in current_desc if d.strip())
            projects.append({"title": current_title, "description": description or current_title})

    for raw_line in lines[start:end]:
        stripped = raw_line.strip()
        if not stripped:
            continue
        is_bullet = stripped.startswith(_BULLET_PREFIXES)
        # A title line: not a bullet, short enough to plausibly be a project
        # name (with an optional tech-stack/date suffix), and not itself a
        # long descriptive sentence.
        looks_like_title = not is_bullet and len(stripped) < 100 and not stripped.endswith(".")
        if looks_like_title:
            flush()
            current_title = re.split(r"\s{2,}|\t|\s[-|]\s", stripped)[0].strip(" :")
            current_desc = []
        else:
            current_desc.append(stripped)

    flush()
    return projects[:10]


def _llm_segment(resume_text: str) -> list[dict] | None:
    prompt = f"""You extract distinct projects from a resume's raw text (personal,
academic, or side projects — not entire job history entries, unless a specific
project is described within one).

Resume text:
\"\"\"{resume_text[:8000]}\"\"\"

For each distinct project, give a concise title and a 1-3 sentence description
covering what was built, the technologies/skills used, and the outcome or
impact if it's stated. Do not invent details that aren't in the resume text.

Respond as JSON with exactly this shape:
{{"projects": [{{"title": "<short project title>", "description": "<1-3 sentence summary>"}}, ...]}}

Return at most 10 projects, in the order they appear in the resume. If no
distinct projects are identifiable, return {{"projects": []}}.
"""

    data = llm_client.generate_json(prompt)
    if not isinstance(data, dict):
        return None

    raw_projects = data.get("projects")
    if not isinstance(raw_projects, list):
        return None

    projects = []
    for item in raw_projects:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        description = item.get("description")
        if isinstance(title, str) and title.strip() and isinstance(description, str):
            projects.append({"title": title.strip(), "description": description.strip()})

    return projects or None


def extract_projects_from_resume(resume_text: str) -> list[dict]:
    """Segments raw resume text into {"title", "description"} project entries,
    ready to hand to `analyze_projects`. Returns [] if no projects are found."""
    if llm_client.is_available():
        result = _llm_segment(resume_text)
        if result is not None:
            return result

    return _heuristic_segment(resume_text)
