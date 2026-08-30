from datetime import datetime

from pydantic import BaseModel


class MatchRequest(BaseModel):
    resume_id: int
    job_ids: list[int] | None = None  # None = match against all recently collected jobs


class JobMatchOut(BaseModel):
    id: int
    job_id: int
    resume_id: int
    match_score: float
    matched_skills: str
    missing_skills: str
    semantic_score: float | None
    is_saved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillDemand(BaseModel):
    skill: str
    percentage: float
    job_count: int


class MarketIntelligenceOut(BaseModel):
    target_role: str
    jobs_analyzed: int
    top_skills: list[SkillDemand]
    skill_gaps: list[str]
