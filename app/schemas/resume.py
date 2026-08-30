from datetime import datetime

from pydantic import BaseModel


class ResumeOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ResumeProjectOut(BaseModel):
    id: int
    title: str
    description: str
    category: str | None
    is_repetitive: bool

    model_config = {"from_attributes": True}


class ResumeAnalysisOut(BaseModel):
    id: int
    resume_id: int
    job_id: int | None
    ats_score: float
    skill_match_pct: float
    matched_keywords: str
    missing_keywords: str
    strengths: str
    weaknesses: str
    missing_strengths: str
    suggestions: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeAnalysisRequest(BaseModel):
    resume_id: int
    job_id: int | None = None


class ProjectSubmission(BaseModel):
    title: str
    description: str


class ProjectAnalysisRequest(BaseModel):
    resume_id: int
    projects: list[ProjectSubmission]


class ProjectAutoAnalysisRequest(BaseModel):
    resume_id: int


class ProjectAnalysisOut(BaseModel):
    projects: list[ResumeProjectOut]
    suggestions: list[str]
