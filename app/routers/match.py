from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import JobMatch, JobPosting, Resume, User
from app.schemas.match import JobMatchOut, MarketIntelligenceOut, MatchRequest, SkillDemand
from app.services import job_matcher, market_intelligence

router = APIRouter(prefix="/match", tags=["match"])


@router.post("", response_model=list[JobMatchOut])
def match_jobs(
    payload: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    query = db.query(JobPosting)
    if payload.job_ids:
        query = query.filter(JobPosting.id.in_(payload.job_ids))
    jobs = query.order_by(JobPosting.collected_at.desc()).limit(100).all()

    ranked = job_matcher.rank_jobs(resume.raw_text, [(job.id, job.description) for job in jobs])

    saved_matches = []
    for result in ranked:
        match = JobMatch(
            user_id=current_user.id,
            job_id=result.job_id,
            resume_id=resume.id,
            match_score=result.match_score,
            matched_skills=", ".join(sorted(result.matched_skills)),
            missing_skills=", ".join(sorted(result.missing_skills)),
            semantic_score=result.semantic_score,
        )
        db.add(match)
        saved_matches.append(match)

    db.commit()
    for match in saved_matches:
        db.refresh(match)

    return saved_matches


@router.post("/{match_id}/save", response_model=JobMatchOut)
def save_match(match_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    match = db.query(JobMatch).filter(JobMatch.id == match_id, JobMatch.user_id == current_user.id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    match.is_saved = True
    db.commit()
    db.refresh(match)
    return match


@router.get("/saved", response_model=list[JobMatchOut])
def list_saved_matches(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(JobMatch)
        .filter(JobMatch.user_id == current_user.id, JobMatch.is_saved.is_(True))
        .order_by(JobMatch.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/market-intelligence", response_model=MarketIntelligenceOut)
def market_intelligence_dashboard(
    target_role: str,
    resume_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = db.query(JobPosting).filter(JobPosting.title.ilike(f"%{target_role}%")).all()

    resume_text = ""
    if resume_id:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
        resume_text = resume.raw_text if resume else ""

    demand, gaps = market_intelligence.analyze_market([job.description for job in jobs], resume_text)

    return MarketIntelligenceOut(
        target_role=target_role,
        jobs_analyzed=len(jobs),
        top_skills=[SkillDemand(skill=d.skill, percentage=d.percentage, job_count=d.job_count) for d in demand],
        skill_gaps=gaps,
    )
