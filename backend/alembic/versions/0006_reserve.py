"""0006: резерв с клиентом и сроком

Добавляет в artworks:
- reserved_client_id — за каким клиентом зарезервирована работа (FK clients.id);
- reserved_until — до какой даты держим резерв;
- reserve_note — комментарий к резерву.

Поля очищаются при смене статуса с reserved на любой другой.

Revision ID: 0006_reserve  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0006_reserve"
down_revision = "0005_storage_and_style"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artworks",
        sa.Column(
            "reserved_client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("artworks", sa.Column("reserved_until", sa.Date(), nullable=True))
    op.add_column("artworks", sa.Column("reserve_note", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "reserve_note")
    op.drop_column("artworks", "reserved_until")
    op.drop_column("artworks", "reserved_client_id")
