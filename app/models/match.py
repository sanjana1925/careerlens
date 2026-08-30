from datetime import datetime, timezone

from sqlalchemy import Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobMatch(Base):
    """Explainable match score between a user's resume and a job posting."""

    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), nullable=False)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False)

    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_skills: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    missing_skills: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Chroma/LangChain secondary signal

    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="job_matches")
    job: Mapped["JobPosting"] = relationship(back_populates="matches")
