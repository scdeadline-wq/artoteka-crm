"""baseline — точка отсчёта для alembic

Схема создавалась через Base.metadata.create_all(). Эта ревизия пустая —
её роль только в том, чтобы зафиксировать «текущее состояние БД до начала
использования alembic».

На существующих базах применять через `alembic stamp 0001_baseline`.
На новых — `alembic upgrade head` после Base.metadata.create_all().

Revision ID: 0001_baseline
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
