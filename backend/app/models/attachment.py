import enum
from datetime import datetime

from sqlalchemy import String, Enum, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttachmentKind(str, enum.Enum):
    expertise = "expertise"
    framing = "framing"


class ArtworkAttachment(Base):
    __tablename__ = "artwork_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    kind: Mapped[AttachmentKind] = mapped_column(Enum(AttachmentKind), index=True)
    url: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str | None] = mapped_column(String(300), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped["Artwork"] = relationship(back_populates="attachments")
