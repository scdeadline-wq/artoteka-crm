"""0009: подборка работ под клиента

client_selections: какие работы предложить клиенту (shortlist) и какие
отправлены ему на просмотр (sent). Уникальная пара (client_id, artwork_id).

Revision ID: 0009_selection  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0009_selection"
down_revision = "0008_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("artwork_id", sa.Integer(), sa.ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="shortlist"),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "artwork_id", name="uq_selection_client_artwork"),
    )


def downgrade() -> None:
    op.drop_table("client_selections")
