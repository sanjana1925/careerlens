# CareerLens AI

Explainable job search, resume intelligence, and career optimization platform.

## Status

Working auth, database models, API routes, and a React frontend. Resume/project
analysis (`app/services/ats_scorer.py`, `project_analyzer.py`) uses Gemini for
the narrative parts (strengths/weaknesses/suggestions, project categorization)
when `GEMINI_API_KEY` is set in `.env`, and transparently falls back to the
original keyword-heuristic scoring when it isn't (or if the Gemini call fails)
— so the app always runs end-to-end, with or without a key. The score itself
and matched/missing keyword lists stay deterministic either way, via
`app/utils/skills.py`.

## Features (scaffolded)

1. **Multi-platform job discovery** — `app/services/job_scraper.py` wraps JobSpy
   (LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri), cleans + dedupes results.
2. **Resume strength/weakness analysis** — `app/services/ats_scorer.py`.
3. **ATS compatibility checker** — same module, scored against a specific job description.
4. **Project quality & repetition detector** — `app/services/project_analyzer.py`.
5. **Personalized job match & ranking** — `app/services/job_matcher.py`.
6. **Explainable match analysis** — matched/missing skills returned alongside every score.
7. **Resume/career improvement suggestions** — generated as part of ATS + project analysis.
8. **Job market & skill intelligence dashboard** — `app/services/market_intelligence.py`.

Auth: JWT-based registration/login with bcrypt password hashing (`app/auth/`).

## Tech Stack

Python, FastAPI, SQLAlchemy, Pydantic, JobSpy, SQLite (swap `DATABASE_URL` for Postgres).

## Project Structure

```text
careerlens-ai/
├── app/
│   ├── main.py              FastAPI app, router registration, table creation
│   ├── config.py            Settings (.env)
│   ├── database.py          SQLAlchemy engine/session/Base
│   ├── models/               Users, Resumes, ResumeAnalyses, ResumeProjects, JobPostings, JobMatches, SearchHistory
│   ├── schemas/              Pydantic request/response models
│   ├── auth/                 Password hashing, JWT, get_current_user dependency
│   ├── routers/               /auth, /resumes, /jobs, /match, /dashboard
│   ├── services/
│   │   ├── job_scraper.py         JobSpy wrapper + clean/dedupe + persist
│   │   ├── resume_parser.py       PDF/DOCX/TXT text extraction
│   │   ├── ats_scorer.py          ATS score, strengths/weaknesses, suggestions (Gemini-narrated)
│   │   ├── project_analyzer.py    Repetitive-project detection (Gemini-categorized)
│   │   ├── llm_client.py          Gemini wrapper — best-effort, falls back to heuristics
│   │   ├── job_matcher.py         Explainable resume<->job match scoring
│   │   └── market_intelligence.py Skill-demand aggregation across jobs
│   └── utils/skills.py       Shared skill keyword vocabulary
├── frontend/                 React (Vite) UI — dashboard, job search, resume
│                              analysis, match, market intelligence
├── requirements.txt
└── .env.example
```

## Setup

### Backend

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # then edit JWT_SECRET_KEY
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

> **Python 3.13 note:** `python-jobspy==1.1.75` pins `numpy==1.26.3`, which has
> no prebuilt wheel for Python 3.13 (pip tries to compile from source and
> fails without a C compiler). If `pip install -r requirements.txt` fails on
> numpy, install a modern numpy/pandas first, then install jobspy without its
> pinned deps:
> ```bash
> pip install --only-binary=:all: "numpy>=2" "pandas>=2.2.3,<3.0.0"
> pip install --no-deps python-jobspy==1.1.75
> pip install beautifulsoup4 markdownify regex requests tls-client
> pip install -r requirements.txt   # picks up the rest (fastapi, sqlalchemy, etc.)
> ```

### Frontend

React (Vite) app in `frontend/`, talks to the API via a dev-server proxy at `/api`.

```bash
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173 (or the next free port) and proxies `/api/*` to
`http://127.0.0.1:8000` (override with `VITE_BACKEND_URL`). The backend has
CORS enabled for any `localhost`/`127.0.0.1` origin, so it also works without
the proxy if you point `frontend/src/api/client.js`'s `BASE_URL` straight at
the API.

## API Flow

```text
POST /auth/register, /auth/login
POST /jobs/search              -> collects + stores jobs for a target role
POST /resumes/upload           -> stores parsed resume text
POST /resumes/analyze          -> ATS score + strengths/weaknesses (optionally vs one job)
POST /resumes/projects/analyze -> repetition/diversity findings
POST /match                    -> explainable match scores against collected jobs
POST /match/{id}/save          -> save a job match
GET  /match/market-intelligence -> skill-demand dashboard for a target role
GET  /dashboard/summary        -> resume count, saved jobs, recent searches
```

## Limitations

**Auth is effectively single-user right now.** The backend has real per-user
JWT auth (`app/auth/`), but the frontend no longer exposes login/register UI —
on load it silently signs into one hardcoded shared account
(`demo@careerlens.app` / `demo-password-123`, see `frontend/src/context/AuthContext.jsx`).
Every browser hitting this frontend shares the same resumes, searches, and
saved matches. Multi-user use requires calling `/auth/register` + `/auth/login`
directly (still fully functional) and dropping in a real login screen.

**Secrets need attention before any real deployment.**
- `.env`'s `JWT_SECRET_KEY` is still the placeholder value from `.env.example`
  — anyone with the repo can forge tokens until it's changed.
- The demo password above is hardcoded in frontend source, i.e. visible in the
  shipped JS bundle. Fine for local use, not for a public deploy.

**LLM output isn't verified.** When `GEMINI_API_KEY` is set, `ats_scorer.py`
and `project_analyzer.py` hand the model a prompt and trust its JSON back —
there's no fact-check pass, so strengths/weaknesses text or a project
category can be subtly wrong (hallucinated specifics, mis-scored category).
The numeric ATS score and matched/missing keyword lists are unaffected (they
stay heuristic/deterministic either way), but the narrative text around them
is not guaranteed accurate. Each analysis also costs one Gemini call — no
caching, so re-running the same analysis re-spends quota and adds ~1–3s
latency.

**Skill detection is a fixed ~50-term keyword list.** `app/utils/skills.py`
backs ATS scoring, job matching, *and* market intelligence. A skill, tool, or
framework not in that list is invisible everywhere — matched/missing
keywords, match score, and skill-demand charts all silently miss it,
regardless of whether Gemini is configured.

**JobSpy scraping has no error isolation.** `job_scraper.scrape_jobs` doesn't
catch exceptions — if JobSpy chokes on one source (site layout change,
rate-limiting, CAPTCHA, network blip), the whole `/jobs/search` request fails
with a 500 instead of returning partial results from the sources that did
work. There's also no retry and no request throttling on this or any other
endpoint, so a scripted client can hammer external job boards or burn Gemini
quota with no limit. Scraping job boards may also be against those sites'
terms of service — that's on you to confirm for your use case.

**Resume upload is unvalidated.** No file size cap, no real content-type
check beyond the filename extension, no malware scanning. A malformed PDF/DOCX
can raise an unhandled parser exception that surfaces as a generic 500 rather
than a clean 400.

**Market intelligence only sees what you've already searched for.**
`/match/market-intelligence` filters previously-collected postings by
`title ILIKE '%role%'` — it's a view over your own search history, not a live
or comprehensive market snapshot, and won't match role names it wasn't given.

**No automated tests.** Everything so far has been verified by manual/ad-hoc
smoke testing (curl + a headless-browser walkthrough), not a regression-safe
test suite — refactors have no safety net yet.

**Other gaps:**
- Automatic resume-to-project segmentation isn't implemented — `/resumes/projects/analyze`
  expects the caller to submit already-split project title/description pairs.
- No Alembic migrations; tables are created via `Base.metadata.create_all`, so
  schema changes require a manual DB reset in development.
- SQLite has no real concurrent-write story; fine for one user, not for
  production traffic.
- List endpoints (`/jobs`, `/resumes`, etc.) have no pagination — they return
  everything up to a fixed `limit`, so they won't scale to large datasets.
- CORS is open to any `localhost`/`127.0.0.1` origin (regex match) for dev
  convenience — tighten this before deploying anywhere public.
