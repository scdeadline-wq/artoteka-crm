"""FEEDBACK_V2 П1: складской номер, soft-delete, теги, рамка

- warehouse_number TEXT — физическое местонахождение работы на складе
- is_framed BOOLEAN DEFAULT FALSE — обрамлена ли работа
- tags TEXT[] — теги/хэштеги (#пейзаж, #портрет и т.п.)
- deleted_at TIMESTAMPTZ — мягкое удаление, NULL = активна

Revision ID: 0002_feedback_v2_p1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_feedback_v2_p1"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artworks",
        sa.Column("warehouse_number", sa.Text(), nullable=True),
    )
    op.add_column(
        "artworks",
        sa.Column(
            "is_framed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "artworks",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "artworks",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_artworks_tags",
        "artworks",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index("ix_artworks_deleted_at", "artworks", ["deleted_at"])
    op.create_index("ix_artworks_is_framed", "artworks", ["is_framed"])
    op.create_index("ix_artworks_sale_price", "artworks", ["sale_price"])


def downgrade() -> None:
    op.drop_index("ix_artworks_sale_price", table_name="artworks")
    op.drop_index("ix_artworks_is_framed", table_name="artworks")
    op.drop_index("ix_artworks_deleted_at", table_name="artworks")
    op.drop_index("ix_artworks_tags", table_name="artworks")
    op.drop_column("artworks", "deleted_at")
    op.drop_column("artworks", "tags")
    op.drop_column("artworks", "is_framed")
    op.drop_column("artworks", "warehouse_number")
