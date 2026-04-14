from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    referral_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), default=None)
    sold_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    referral_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    artwork: Mapped["Artwork"] = relationship()
    client: Mapped["Client"] = relationship(back_populates="purchases", foreign_keys=[client_id])
    referral: Mapped["Client | None"] = relationship(foreign_keys=[referral_id])
