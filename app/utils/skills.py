"""Shared skill vocabulary used for keyword extraction across resumes and job descriptions.

Organized as a flat, hand-picked taxonomy (with aliases) so ATS scoring / matching /
market intelligence work without an LLM call. Swap for a taxonomy service or NER
model later without changing the callers below.
"""

import re
from dataclasses import dataclass

# Canonical skill name -> category. Keep canonical names lowercase; extract_skills
# always returns canonical names even when an alias is what matched.
SKILL_CATEGORIES: dict[str, list[str]] = {
    "languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "rust",
        "r", "php", "ruby", "kotlin", "swift", "scala", "sql", "bash", "shell scripting",
        "matlab", "perl", "dart", "html", "css",
        "objective-c", "julia", "elixir", "haskell", "lua", "assembly",
    ],
    "frontend": [
        "react", "angular", "vue.js", "next.js", "svelte", "redux", "tailwind css",
        "bootstrap", "jquery", "webpack", "vite",
        "solid.js", "remix", "astro", "sass", "less", "storybook",
    ],
    "backend": [
        "node.js", "express.js", "fastapi", "django", "flask", "spring boot",
        "ruby on rails", "laravel", "asp.net", ".net core", "nestjs",
        "quarkus", "micronaut", "phoenix framework",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle",
        "microsoft sql server", "cassandra", "dynamodb", "elasticsearch",
        "neo4j", "firebase", "supabase",
        "cockroachdb", "clickhouse", "influxdb", "couchbase", "mariadb",
    ],
    "cloud_devops": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "jenkins", "github actions", "gitlab ci", "ci/cd", "nginx", "linux",
        "serverless", "cloudformation", "helm", "prometheus", "grafana",
        "digitalocean", "vercel", "netlify", "pulumi", "istio", "argo cd",
        "datadog", "new relic", "sentry",
    ],
    "data_ml_ai": [
        "machine learning", "deep learning", "nlp", "computer vision", "pytorch",
        "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "matplotlib",
        "rag", "llm", "langchain", "prompt engineering", "vector database",
        "ai agents", "openai api", "gemini api", "hugging face", "mlflow",
        "reinforcement learning", "generative ai", "xgboost", "opencv",
        "anthropic api", "llamaindex", "faiss", "pinecone", "weaviate", "qdrant",
        "stable diffusion", "onnx", "ray",
    ],
    "data_engineering": [
        "airflow", "spark", "kafka", "hadoop", "etl", "dbt", "snowflake",
        "databricks", "bigquery", "redshift", "tableau", "power bi", "looker",
        "fivetran", "dagster", "prefect", "delta lake", "presto", "trino",
    ],
    "apis_architecture": [
        "rest api", "graphql", "microservices", "grpc", "websockets", "oauth",
        "api gateway",
        "rabbitmq", "message queues", "event-driven architecture", "webhooks",
    ],
    "tools_methodology": [
        "git", "github", "gitlab", "jira", "confluence", "agile", "scrum",
        "kanban", "tdd", "unit testing", "postman", "figma", "pytest",
        "notion", "cypress", "playwright", "jest", "selenium", "sonarqube",
    ],
    "mobile": [
        "android", "ios", "react native", "flutter", "swiftui",
        "jetpack compose", "kotlin multiplatform", "expo", "capacitor",
    ],
}

# Alternate spellings/abbreviations that should still resolve to the canonical
# skill name above. Not every skill needs an entry here.
SKILL_ALIASES: dict[str, list[str]] = {
    "javascript": ["js"],
    "typescript": ["ts"],
    "c++": ["cpp"],
    "c#": ["csharp", "c sharp"],
    "go": ["golang"],
    "shell scripting": ["shell script", "bash scripting"],
    "vue.js": ["vue", "vuejs"],
    "next.js": ["nextjs", "next js"],
    "tailwind css": ["tailwind"],
    "node.js": ["nodejs", "node js"],
    "express.js": ["express", "expressjs"],
    "spring boot": ["springboot"],
    "ruby on rails": ["rails"],
    ".net core": ["dotnet core", ".net", "dotnet"],
    "postgresql": ["postgres", "psql"],
    "microsoft sql server": ["mssql", "sql server", "t-sql"],
    "elasticsearch": ["elastic search"],
    "dynamodb": ["dynamo db"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud", "google cloud platform"],
    "kubernetes": ["k8s"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment"],
    "github actions": ["github ci"],
    "gitlab ci": ["gitlab ci/cd"],
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "nlp": ["natural language processing"],
    "computer vision": ["cv"],
    "scikit-learn": ["sklearn"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "llm": ["large language model", "large language models", "llms"],
    "ai agents": ["agentic ai", "autonomous agents", "ai agent"],
    "generative ai": ["genai", "gen ai"],
    "hugging face": ["huggingface"],
    "prompt engineering": ["prompt design"],
    "vector database": ["vector db", "vector store"],
    "openai api": ["openai", "chatgpt api"],
    "gemini api": ["gemini"],
    "power bi": ["powerbi"],
    "bigquery": ["big query"],
    "rest api": ["restful api", "rest apis", "restful apis"],
    "graphql": ["graph ql"],
    "microservices": ["microservice architecture", "microservice"],
    "unit testing": ["unit tests"],
    "react native": ["reactnative"],
    "ios": ["iphone development", "ios development"],
    "android": ["android development"],
    "objective-c": ["objective c", "objc"],
    "solid.js": ["solidjs", "solid js"],
    "cockroachdb": ["cockroach db"],
    "argo cd": ["argocd"],
    "new relic": ["newrelic"],
    "anthropic api": ["claude api", "anthropic"],
    "llamaindex": ["llama index"],
    "delta lake": ["deltalake"],
    "message queues": ["message queue"],
    "event-driven architecture": ["event driven architecture"],
}

# Flat, deduped list of every canonical skill across categories.
SKILL_VOCABULARY: list[str] = sorted({skill for skills in SKILL_CATEGORIES.values() for skill in skills})

_SKILL_TO_CATEGORY: dict[str, str] = {
    skill: category for category, skills in SKILL_CATEGORIES.items() for skill in skills
}


def skill_category(skill: str) -> str | None:
    """Category a canonical skill name belongs to, or None if not in the taxonomy."""
    return _SKILL_TO_CATEGORY.get(skill)


def _terms_for(skill: str) -> list[str]:
    return [skill, *SKILL_ALIASES.get(skill, [])]


def _compile_pattern(skill: str) -> re.Pattern:
    alternatives = "|".join(r"(?<!\w)" + re.escape(term) + r"(?!\w)" for term in _terms_for(skill))
    return re.compile(alternatives, re.IGNORECASE)


# Precompiled once at import time for every skill in the default vocabulary —
# extract_skills is called on every resume/job-description analysis, so this
# avoids recompiling ~150 regexes (plus their aliases) on every call.
_COMPILED_PATTERNS: dict[str, re.Pattern] = {skill: _compile_pattern(skill) for skill in SKILL_VOCABULARY}


def extract_skills(text: str, vocabulary: list[str] = SKILL_VOCABULARY) -> set[str]:
    """Word-boundary matching (including aliases) so short skills (e.g. "r", "go")
    don't false-positive inside unrelated words (e.g. "developer", "algorithm"),
    and so "k8s"/"postgres"/"js" etc. still resolve to their canonical skill name."""
    matched = set()
    for skill in vocabulary:
        pattern = _COMPILED_PATTERNS.get(skill) or _compile_pattern(skill)
        if pattern.search(text):
            matched.add(skill)
    return matched


@dataclass
class SkillMatch:
    score: float
    matched: set[str]
    missing: set[str]


def score_skills(candidate_skills: set[str], target_skills: set[str]) -> SkillMatch:
    """Shared matched/missing/score core for resume<->job keyword matching.

    Single implementation used by both app/services/job_matcher.py (resume vs
    many jobs) and app/services/ats_scorer.py (resume vs one job description,
    or vs the resume's own category vocabulary when no job is given) — they
    used to each compute this inline, which meant the same "matched / total"
    formula existed twice and could silently drift apart.
    """
    matched = candidate_skills & target_skills
    missing = target_skills - candidate_skills
    score = round(100 * len(matched) / len(target_skills), 1) if target_skills else 0.0
    return SkillMatch(score=score, matched=matched, missing=missing)
