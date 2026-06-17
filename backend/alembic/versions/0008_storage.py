"""0008: справочники хранения (склад/стеллаж/полка)

- Таблица storage_options (kind: warehouse|rack|shelf, name) — выпадающие списки, ведёт админ.
- artworks: warehouse_id/rack_id/shelf_id (FK → storage_options, ON DELETE SET NULL).
- Миграция данных: location/rack/shelf (текст) → опции справочника + проставляем FK.
- Старые текстовые колонки location, rack, shelf удаляются (как warehouse_number в 0003).

Revision ID: 0008_storage  (≤32 символов — иначе деплой падает, см. 0004)
"""
import sqlalchemy as sa
from alembic import op


revision = "0008_storage"
down_revision = "0007_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "storage_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False, index=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("kind", "name", name="uq_storage_kind_name"),
    )

    op.add_column("artworks", sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("storage_options.id", ondelete="SET NULL"), nullable=True))
    op.add_column("artworks", sa.Column("rack_id", sa.Integer(), sa.ForeignKey("storage_options.id", ondelete="SET NULL"), nullable=True))
    op.add_column("artworks", sa.Column("shelf_id", sa.Integer(), sa.ForeignKey("storage_options.id", ondelete="SET NULL"), nullable=True))

    # Переносим существующие текстовые значения в справочник и проставляем FK
    for kind, col in (("warehouse", "location"), ("rack", "rack"), ("shelf", "shelf")):
        op.execute(
            f"""
            INSERT INTO storage_options (kind, name, sort_order)
            SELECT DISTINCT '{kind}', btrim({col}), 0
            FROM artworks
            WHERE {col} IS NOT NULL AND btrim({col}) <> ''
            ON CONFLICT (kind, name) DO NOTHING
            """
        )
        op.execute(
            f"""
            UPDATE artworks a
            SET {kind}_id = s.id
            FROM storage_options s
            WHERE s.kind = '{kind}' AND s.name = btrim(a.{col})
              AND a.{col} IS NOT NULL AND btrim(a.{col}) <> ''
            """
        )

    op.drop_column("artworks", "location")
    op.drop_column("artworks", "rack")
    op.drop_column("artworks", "shelf")


def downgrade() -> None:
    op.add_column("artworks", sa.Column("location", sa.String(length=300), nullable=True))
    op.add_column("artworks", sa.Column("rack", sa.String(length=100), nullable=True))
    op.add_column("artworks", sa.Column("shelf", sa.String(length=100), nullable=True))

    for kind, col in (("warehouse", "location"), ("rack", "rack"), ("shelf", "shelf")):
        op.execute(
            f"""
            UPDATE artworks a
            SET {col} = s.name
            FROM storage_options s
            WHERE s.id = a.{kind}_id
            """
        )

    op.drop_column("artworks", "shelf_id")
    op.drop_column("artworks", "rack_id")
    op.drop_column("artworks", "warehouse_id")
    op.drop_table("storage_options")
