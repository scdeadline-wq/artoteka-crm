from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Mockup(Base):
    __tablename__ = "mockups"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"))
    room_image_url: Mapped[str] = mapped_column(String(500))
    result_image_url: Mapped[str] = mapped_column(String(500))
    style: Mapped[str] = mapped_column(String(50), default="custom")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped["Artwork"] = relationship()
