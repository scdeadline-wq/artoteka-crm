from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShareLink(Base):
    """Публичная ссылка на подборку работ (по художникам и/или тегам; без фильтров — весь каталог).

    Подборка «живая»: фильтр хранится, а не список работ — новые работы автора
    сами появляются по ссылке. Черновики, проданные и удалённые не показываются.
    """

    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    artist_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    only_available: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # только «В продаже»
    show_prices: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
