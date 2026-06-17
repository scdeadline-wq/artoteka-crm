"""0007: валюта и app_settings

- Таблица app_settings (key-value настройки: валюта по умолчанию, лого/водяной знак PDF).
- artworks.currency, sales.currency (код валюты, server_default 'USD') — без привязки к курсу.

Revision ID: 0007_currency  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0007_currency"
down_revision = "0006_reserve"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.add_column(
        "artworks",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
    )
    op.add_column(
        "sales",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
    )


def downgrade() -> None:
    op.drop_column("sales", "currency")
    op.drop_column("artworks", "currency")
    op.drop_table("app_settings")
