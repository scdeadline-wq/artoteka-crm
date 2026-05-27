from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, ORMExecuteState, Session, with_loader_criteria

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(Session, "do_orm_execute")
def _soft_delete_filter(state: ORMExecuteState) -> None:
    if not state.is_select:
        return
    if state.execution_options.get("include_deleted", False):
        return
    from app.models.artwork import Artwork

    state.statement = state.statement.options(
        with_loader_criteria(
            Artwork,
            lambda cls: cls.deleted_at.is_(None),
            include_aliases=True,
        )
    )


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
