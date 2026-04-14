from datetime import datetime

from sqlalchemy import String, Boolean, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ru: Mapped[str] = mapped_column(String(300), index=True)
    name_en: Mapped[str | None] = mapped_column(String(300), default=None)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    bio: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artworks: Mapped[list["Artwork"]] = relationship(back_populates="artist")
