"""Этап A: справочник комнат + роль admin

- Новая роль `admin` в enum userrole (между owner и manager по правам).
- Таблица `rooms` (id, name, sort_order, created_at).
- artworks.room_id FK → rooms(id) ON DELETE SET NULL.
- Каждое уникальное непустое warehouse_number → запись в rooms;
  artworks.room_id проставляется соответствующим id.
- Колонка warehouse_number удаляется.

Revision ID: 0003_rooms_and_admin_role
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_rooms_and_admin_role"
down_revision = "0002_feedback_v2_p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Добавить значение 'admin' в существующий enum userrole.
    # ALTER TYPE ... ADD VALUE не работает внутри транзакции в старых версиях
    # Postgres; в современных (>=12) работает. Выполняем через autocommit-блок.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin' AFTER 'owner'")

    # 2. Таблица rooms.
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 3. Колонка room_id.
    op.add_column(
        "artworks",
        sa.Column("room_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_artworks_room_id",
        source_table="artworks",
        referent_table="rooms",
        local_cols=["room_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_artworks_room_id", "artworks", ["room_id"])

    # 4. Перенос данных: distinct warehouse_number → rooms; UPDATE artworks.room_id.
    op.execute(
        """
        INSERT INTO rooms (name, sort_order)
        SELECT DISTINCT TRIM(warehouse_number), 0
        FROM artworks
        WHERE warehouse_number IS NOT NULL
          AND TRIM(warehouse_number) <> ''
        """
    )
    op.execute(
        """
        UPDATE artworks a
        SET room_id = r.id
        FROM rooms r
        WHERE TRIM(a.warehouse_number) = r.name
        """
    )

    # 5. Удалить старую колонку.
    op.drop_column("artworks", "warehouse_number")


def downgrade() -> None:
    # Вернуть warehouse_number и заполнить из rooms.name.
    op.add_column(
        "artworks",
        sa.Column("warehouse_number", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE artworks a
        SET warehouse_number = r.name
        FROM rooms r
        WHERE a.room_id = r.id
        """
    )
    op.drop_index("ix_artworks_room_id", table_name="artworks")
    op.drop_constraint("fk_artworks_room_id", "artworks", type_="foreignkey")
    op.drop_column("artworks", "room_id")
    op.drop_table("rooms")
    # Откатить добавление значения enum нельзя без пересоздания типа —
    # оставляем 'admin' в userrole. Безвредно: записей с такой ролью не будет
    # после отката кода.
