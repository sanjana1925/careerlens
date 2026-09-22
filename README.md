<div align="center">

# 🧭 CareerLens AI

### Explainable job search & resume intelligence

CareerLens AI scores your resume against real job postings, discovers matching roles across multiple platforms, and shows exactly which skills are closing — or blocking — the gap, with every number traceable back to the keywords that produced it.

</div>

- 🎯 **Explainable ATS Scoring** — deterministic keyword matching against a 200+ term skill taxonomy, narrated by Gemini with a built-in heuristic fallback, via `app/services/ats_scorer.py`
- 🔍 **Multi-Platform Job Discovery** — scrapes LinkedIn, Indeed, Glassdoor, Google Jobs, and ZipRecruiter through JobSpy, deduped and persisted automatically, via `app/services/job_scraper.py`
- 🧩 **Explainable Job Matching** — ranks collected postings against a resume with matched/missing skill breakdowns, plus a semantic layer from Chroma + LangChain, via `app/services/job_matcher.py`
- 🔁 **Project Repetition Detector** — flags resume projects that repeat the same conceptual pattern and suggests diversification, via `app/services/project_analyzer.py`
- 📊 **Market Intelligence Dashboard** — aggregates in-demand skills across collected postings and surfaces personalized skill gaps, via `app/services/market_intelligence.py`
- 🔐 **JWT Auth & FastAPI Backend** — SQLAlchemy models, bcrypt password hashing, and a React (Vite) frontend served from the same origin

<br>

---

<br>

<div align="center">

## 🏗️ Architecture
<br>

<img src="architecture.svg" alt="CareerLens AI architecture diagram" width="850">

*A request flows from the React frontend through FastAPI routers into a deterministic, LLM-independent scoring core, which persists to SQLite while optionally enriching results with JobSpy scrapes and best-effort Gemini/Chroma calls that never block the response if they fail.*

</div>

<br>
