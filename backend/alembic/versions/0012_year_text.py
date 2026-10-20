"""0012: год как текст (интервал, десятилетие)

artworks.year_text — то, что ввёл пользователь: "2016-2017", "2000-е", "конец XIX в.".
artworks.year остаётся числом (начало интервала) — для фильтров и сортировки.

Revision ID: 0012_year_text  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0012_year_text"
down_revision = "0011_exhibition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("year_text", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "year_text")
