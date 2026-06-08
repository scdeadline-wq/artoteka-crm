"""0005: место хранения (стеллаж/полка) + стиль/направление

Добавляет в artworks:
- style_period — стиль/направление (раньше AI его определял, но колонки не было
  и значение выбрасывалось при сохранении; теперь хранится и редактируется);
- rack — стеллаж;
- shelf — полка.

Revision ID: 0005_storage_and_style  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0005_storage_and_style"
down_revision = "0004_on_exhibition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("style_period", sa.Text(), nullable=True))
    op.add_column("artworks", sa.Column("rack", sa.String(length=100), nullable=True))
    op.add_column("artworks", sa.Column("shelf", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "shelf")
    op.drop_column("artworks", "rack")
    op.drop_column("artworks", "style_period")
