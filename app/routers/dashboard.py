from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import JobMatch, JobPosting, Resume, ResumeAnalysis, SearchHistory, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

GOOD_MATCH_THRESHOLD = 50.0
LOW_ATS_SCORE_THRESHOLD = 60.0


class SearchHistoryOut(BaseModel):
    id: int
    target_role: str
    source_platforms: str
    location: str | None
    results_count: int

    model_config = {"from_attributes": True}


class RecommendedJobOut(BaseModel):
    job_id: int
    title: str
    company: str | None
    match_score: float
    url: str


class DashboardSummary(BaseModel):
    resume_count: int
    saved_job_count: int
    total_jobs_found: int
    jobs_matching_profile: int
    ats_resume_score: float | None
    profile_strength: float
    career_readiness_score: float
    top_recommended_jobs: list[RecommendedJobOut]
    recommended_actions: list[str]
    recent_searches: list[SearchHistoryOut]


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    target_role: str | None = None,
    resume_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.uploaded_at.desc()).all()
    resume_count = len(resumes)

    latest_resume = None
    if resume_id:
        latest_resume = next((r for r in resumes if r.id == resume_id), None)
    if latest_resume is None and resumes:
        latest_resume = resumes[0]

    latest_analysis = None
    if latest_resume:
        latest_analysis = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.resume_id == latest_resume.id)
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
    ats_resume_score = latest_analysis.ats_score if latest_analysis else None

    user_matches = db.query(JobMatch).filter(JobMatch.user_id == current_user.id).all()
    has_run_match = len(user_matches) > 0
    saved_job_count = sum(1 for m in user_matches if m.is_saved)

    # Re-running /match against the same collected jobs creates a new JobMatch
    # row each time, so dedupe by job_id (keeping the best score) before using
    # this for "distinct jobs" counts/recommendations.
    best_match_by_job: dict[int, JobMatch] = {}
    for m in user_matches:
        existing = best_match_by_job.get(m.job_id)
        if existing is None or m.match_score > existing.match_score:
            best_match_by_job[m.job_id] = m
    jobs_matching_profile = sum(1 for m in best_match_by_job.values() if m.match_score >= GOOD_MATCH_THRESHOLD)

    total_jobs_found = db.query(JobPosting).count()

    # v1 heuristic: 25 pts each for target role set, a resume uploaded, an
    # analysis run, and a match run — same "explainable, deterministic,
    # upgrade later" approach as app/services/ats_scorer.py.
    profile_strength = 25.0 * sum([
        bool(target_role),
        resume_count > 0,
        latest_analysis is not None,
        has_run_match,
    ])

    top_matches = sorted(best_match_by_job.values(), key=lambda m: m.match_score, reverse=True)[:5]
    avg_top_match_score = sum(m.match_score for m in top_matches) / len(top_matches) if top_matches else 0.0

    career_readiness_score = round(
        profile_strength * 0.3 + (ats_resume_score or 0.0) * 0.4 + avg_top_match_score * 0.3,
        1,
    )

    top_recommended_jobs: list[RecommendedJobOut] = []
    if top_matches:
        job_ids = [m.job_id for m in top_matches]
        jobs_by_id = {j.id: j for j in db.query(JobPosting).filter(JobPosting.id.in_(job_ids)).all()}
        for m in top_matches:
            job = jobs_by_id.get(m.job_id)
            if job:
                top_recommended_jobs.append(
                    RecommendedJobOut(job_id=job.id, title=job.title, company=job.company, match_score=m.match_score, url=job.url)
                )

    recommended_actions: list[str] = []
    if resume_count == 0:
        recommended_actions.append("Upload your resume to get started.")
    elif latest_analysis is None:
        recommended_actions.append("Run an ATS analysis on your resume.")
    if total_jobs_found == 0:
        recommended_actions.append("Search for jobs matching your target role.")
    elif resume_count > 0 and not has_run_match:
        recommended_actions.append("Run job matching to see how your resume fits.")
    if ats_resume_score is not None and ats_resume_score < LOW_ATS_SCORE_THRESHOLD:
        recommended_actions.append(f"Improve your resume — ATS score is below {int(LOW_ATS_SCORE_THRESHOLD)}.")
    if target_role and latest_resume:
        recommended_actions.append("Check Market Intelligence for skill gaps in your target role.")
    recommended_actions = recommended_actions[:4]

    recent_searches = (
        db.query(SearchHistory)
        .filter(SearchHistory.user_id == current_user.id)
        .order_by(SearchHistory.searched_at.desc())
        .limit(10)
        .all()
    )

    return DashboardSummary(
        resume_count=resume_count,
        saved_job_count=saved_job_count,
        total_jobs_found=total_jobs_found,
        jobs_matching_profile=jobs_matching_profile,
        ats_resume_score=ats_resume_score,
        profile_strength=profile_strength,
        career_readiness_score=career_readiness_score,
        top_recommended_jobs=top_recommended_jobs,
        recommended_actions=recommended_actions,
        recent_searches=recent_searches,
    )
