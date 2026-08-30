from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobPosting(Base):
    """A job posting collected via JobSpy, deduplicated by (source, url)."""

    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("source", "url", name="uq_job_source_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # linkedin, indeed, glassdoor, naukri, google
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    min_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # fulltime, parttime, contract, internship
    is_remote: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    date_posted: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    matches: Mapped[list["JobMatch"]] = relationship(back_populates="job", cascade="all, delete-orphan")
