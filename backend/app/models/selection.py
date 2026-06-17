from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Статусы работы в подборке клиента.
SELECTION_STATUSES = ("shortlist", "sent")  # ⭐ предложить · 📤 отправлено на просмотр


class ClientSelection(Base):
    """Подборка работ под клиента: что предложить (shortlist) и что уже
    отправили ему на просмотр (sent). Одна работа на клиента — одна запись."""

    __tablename__ = "client_selections"
    __table_args__ = (UniqueConstraint("client_id", "artwork_id", name="uq_selection_client_artwork"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="shortlist", server_default="shortlist")
    note: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    artwork: Mapped["Artwork"] = relationship()
