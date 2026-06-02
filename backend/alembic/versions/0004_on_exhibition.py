"""Этап E-13 (мини): статус «на выставке»

Добавляет значение `on_exhibition` в enum artworkstatus.

Revision ID: 0004_on_exhibition

ID укорочен: alembic_version.version_num = varchar(32), а прежний ID
«0004_artwork_status_on_exhibition» = 33 символа → миграция падала на
записи ревизии (StringDataRightTruncation), обрывая весь деплой.
"""
from alembic import op


revision = "0004_on_exhibition"
down_revision = "0003_rooms_and_admin_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE — через autocommit-блок (как в 0003 для userrole).
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE artworkstatus ADD VALUE IF NOT EXISTS 'on_exhibition' AFTER 'collection'"
        )


def downgrade() -> None:
    # Удалить значение из enum в Postgres нельзя без пересоздания типа.
    # Оставляем on_exhibition — безвредно (записей с таким статусом не будет).
    pass
