import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Text, Enum, ForeignKey, Integer, Numeric,
    Boolean, DateTime, Table, Column, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ArtworkStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    for_sale = "for_sale"
    reserved = "reserved"
    sold = "sold"
    collection = "collection"


# Many-to-many: artwork <-> technique
artwork_techniques = Table(
    "artwork_techniques",
    Base.metadata,
    Column("artwork_id", Integer, ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True),
    Column("technique_id", Integer, ForeignKey("techniques.id", ondelete="CASCADE"), primary_key=True),
)


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    inventory_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(500), default=None)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"))
    year: Mapped[int | None] = mapped_column(Integer, default=None)
    edition: Mapped[str | None] = mapped_column(String(100), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    condition: Mapped[str | None] = mapped_column(Text, default=None)
    has_expertise: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[ArtworkStatus] = mapped_column(Enum(ArtworkStatus), default=ArtworkStatus.draft, index=True)
    location: Mapped[str | None] = mapped_column(String(300), default=None)
    width_cm: Mapped[float | None] = mapped_column(Numeric(8, 1), default=None)
    height_cm: Mapped[float | None] = mapped_column(Numeric(8, 1), default=None)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    artist: Mapped["Artist"] = relationship(back_populates="artworks")
    techniques: Mapped[list["Technique"]] = relationship(secondary=artwork_techniques)
    images: Mapped[list["Image"]] = relationship(back_populates="artwork", cascade="all, delete-orphan")
    attachments: Mapped[list["ArtworkAttachment"]] = relationship(back_populates="artwork", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped["Artwork"] = relationship(back_populates="images")
