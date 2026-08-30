from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SearchHistory(Base):
    """Records each job search a user runs, for history and market-trend aggregation."""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    source_platforms: Mapped[str] = mapped_column(String(255), default="")  # comma-separated
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0)

    searched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="search_history")
