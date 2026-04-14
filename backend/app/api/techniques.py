from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models import Technique, User
from app.schemas.technique import TechniqueOut

router = APIRouter()


@router.get("/", response_model=list[TechniqueOut])
async def list_techniques(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Technique).order_by(Technique.category, Technique.name))
    return result.scalars().all()
