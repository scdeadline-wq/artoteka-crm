import enum
from datetime import datetime

from sqlalchemy import (
    String, Text, Enum, Integer, ForeignKey,
    Table, Column, DateTime, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientType(str, enum.Enum):
    buyer = "buyer"
    dealer = "dealer"
    referral = "referral"


# Many-to-many: client <-> preferred artists
client_artists = Table(
    "client_artists",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", Integer, ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True),
)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    email: Mapped[str | None] = mapped_column(String(200), default=None)
    telegram: Mapped[str | None] = mapped_column(String(200), default=None)
    client_type: Mapped[ClientType] = mapped_column(Enum(ClientType), default=ClientType.buyer)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    preferred_artists: Mapped[list["Artist"]] = relationship(secondary=client_artists)
    purchases: Mapped[list["Sale"]] = relationship(back_populates="client", foreign_keys="Sale.client_id")
