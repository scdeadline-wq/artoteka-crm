"""0010: провенанс + внутренние фото

- artworks.provenance (Text) — биография работы (коллекции, выставки, каталоги).
- images.is_internal (Boolean) — внутреннее фото (сертификат, оборот),
  не попадает в клиентский PDF.

Revision ID: 0010_provenance  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0010_provenance"
down_revision = "0009_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("provenance", sa.Text(), nullable=True))
    op.add_column("images", sa.Column("is_internal", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("images", "is_internal")
    op.drop_column("artworks", "provenance")
