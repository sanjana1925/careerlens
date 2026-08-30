from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Resume, ResumeAnalysis, ResumeProject, User
from app.schemas.resume import (
    ProjectAnalysisOut,
    ProjectAnalysisRequest,
    ProjectAutoAnalysisRequest,
    ResumeAnalysisOut,
    ResumeAnalysisRequest,
    ResumeOut,
)
from app.services import ats_scorer, project_analyzer
from app.services.resume_parser import MAX_UPLOAD_BYTES, extract_text

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large — max {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )
    try:
        raw_text = extract_text(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    resume = Resume(user_id=current_user.id, filename=file.filename, raw_text=raw_text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/analyze", response_model=ResumeAnalysisOut)
def analyze_resume(
    payload: ResumeAnalysisRequest,
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

    job_description = ""
    if payload.job_id:
        from app.models import JobPosting

        job = db.query(JobPosting).filter(JobPosting.id == payload.job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        job_description = job.description

    result = ats_scorer.score_resume(resume.raw_text, job_description)

    analysis = ResumeAnalysis(
        resume_id=resume.id,
        job_id=payload.job_id,
        ats_score=result.ats_score,
        skill_match_pct=result.skill_match_pct,
        matched_keywords=", ".join(sorted(result.matched_keywords)),
        missing_keywords=", ".join(sorted(result.missing_keywords)),
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        missing_strengths=result.missing_strengths,
        suggestions=result.suggestions,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/{resume_id}/analyses", response_model=list[ResumeAnalysisOut])
def list_analyses(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.resume_id == resume_id)
        .order_by(ResumeAnalysis.created_at.desc())
        .all()
    )


@router.post("/projects/analyze", response_model=ProjectAnalysisOut)
def analyze_projects(
    payload: ProjectAnalysisRequest,
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

    findings, suggestions = project_analyzer.analyze_projects([p.model_dump() for p in payload.projects])

    saved_projects = []
    for submission, finding in zip(payload.projects, findings):
        project = ResumeProject(
            resume_id=resume.id,
            title=submission.title,
            description=submission.description,
            category=finding.category,
            is_repetitive=finding.is_repetitive,
        )
        db.add(project)
        saved_projects.append(project)

    db.commit()
    for project in saved_projects:
        db.refresh(project)

    return ProjectAnalysisOut(projects=saved_projects, suggestions=suggestions)


@router.post("/projects/auto-analyze", response_model=ProjectAnalysisOut)
def auto_analyze_projects(
    payload: ProjectAutoAnalysisRequest,
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

    extracted = project_analyzer.extract_projects_from_resume(resume.raw_text)
    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect distinct projects in this resume automatically — add them manually instead.",
        )

    findings, suggestions = project_analyzer.analyze_projects(extracted)

    saved_projects = []
    for submission, finding in zip(extracted, findings):
        project = ResumeProject(
            resume_id=resume.id,
            title=submission["title"],
            description=submission["description"],
            category=finding.category,
            is_repetitive=finding.is_repetitive,
        )
        db.add(project)
        saved_projects.append(project)

    db.commit()
    for project in saved_projects:
        db.refresh(project)

    return ProjectAnalysisOut(projects=saved_projects, suggestions=suggestions)
