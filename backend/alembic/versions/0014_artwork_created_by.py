"""0014: кто внёс работу (artworks.created_by_id)

Поле notes уже есть в таблице — теперь это «внутренний комментарий» в UI.
Старые работы остаются с created_by_id = NULL (автор неизвестен).

Revision ID: 0014_artwork_created_by  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0014_artwork_created_by"
down_revision = "0013_share_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artworks",
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artworks", "created_by_id")
