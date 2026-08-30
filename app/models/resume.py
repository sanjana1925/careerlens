from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="resumes")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    projects: Mapped[list["ResumeProject"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class ResumeAnalysis(Base):
    """One ATS/skills/strengths-weaknesses analysis run, optionally scoped to a target job."""

    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job_postings.id"), nullable=True)

    ats_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_match_pct: Mapped[float] = mapped_column(Float, default=0.0)

    matched_keywords: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    missing_keywords: Mapped[str] = mapped_column(Text, default="")  # comma-separated

    strengths: Mapped[str] = mapped_column(Text, default="")
    weaknesses: Mapped[str] = mapped_column(Text, default="")
    missing_strengths: Mapped[str] = mapped_column(Text, default="")  # strong points the resume lacks for this target
    suggestions: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    resume: Mapped["Resume"] = relationship(back_populates="analyses")


class ResumeProject(Base):
    """A project extracted from a resume, used by the repetition/quality detector."""

    __tablename__ = "resume_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "supervised-ml-prediction"
    is_repetitive: Mapped[bool] = mapped_column(Boolean, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="projects")
