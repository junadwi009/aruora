"""Register the practice-receipt entity without importing models recursively."""
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

def register_practice_model(base):
    class PracticeSession(base):
        __tablename__ = "practice_sessions"
        __table_args__ = (Index("ix_practice_owner_expiry", "user_id", "expires_at"),)
        id: Mapped[str] = mapped_column(String(32), primary_key=True)
        user_id: Mapped[int] = mapped_column(ForeignKey("user_profile.id", ondelete="CASCADE"))
        skill: Mapped[str] = mapped_column(String(20))
        band: Mapped[str] = mapped_column(String(6))
        status: Mapped[str] = mapped_column(String(16), default="open")
        snapshot: Mapped[dict] = mapped_column(JSON)
        answer_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
        result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    return PracticeSession
