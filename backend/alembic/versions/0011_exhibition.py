"""0011: выставка с точными сроками

Поля на artworks для статуса on_exhibition (по аналогии с резервом):
- exhibition_from / exhibition_to — даты начала/конца;
- exhibition_place — площадка/заметка.
Очищаются при смене статуса с on_exhibition на другой.

Revision ID: 0011_exhibition  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0011_exhibition"
down_revision = "0010_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("exhibition_from", sa.Date(), nullable=True))
    op.add_column("artworks", sa.Column("exhibition_to", sa.Date(), nullable=True))
    op.add_column("artworks", sa.Column("exhibition_place", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "exhibition_place")
    op.drop_column("artworks", "exhibition_to")
    op.drop_column("artworks", "exhibition_from")
