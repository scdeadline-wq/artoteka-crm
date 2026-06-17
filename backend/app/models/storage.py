from datetime import datetime

from sqlalchemy import String, Integer, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Виды мест хранения. Каждый — отдельный выпадающий список, который ведёт админ.
STORAGE_KINDS = ("warehouse", "rack", "shelf")  # склад/адрес · стеллаж · полка


class StorageOption(Base):
    """Справочник мест хранения. Один разделяемый список с дискриминатором kind:
    склад (адрес), стеллаж, полка. Комнаты — отдельная сущность Room."""

    __tablename__ = "storage_options"
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_storage_kind_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
