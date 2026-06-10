from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models import Technique, User
from app.schemas.technique import TechniqueCreate, TechniqueOut

router = APIRouter()


@router.get("/", response_model=list[TechniqueOut])
async def list_techniques(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Technique).order_by(Technique.category, Technique.name))
    return result.scalars().all()


@router.post("/", response_model=TechniqueOut, status_code=201)
async def create_technique(
    body: TechniqueCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Добавить свою технику в справочник. Если такая (без учёта регистра)
    уже есть — возвращаем существующую, чтобы не плодить дубли."""
    name = body.name.strip()
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Название техники пустое")

    existing = (await db.execute(
        select(Technique).where(func.lower(Technique.name) == name.lower())
    )).scalar_one_or_none()
    if existing:
        return existing

    technique = Technique(name=name, category=(body.category or "Прочее"))
    db.add(technique)
    try:
        await db.commit()
    except IntegrityError:
        # Гонка check-then-insert: кто-то успел создать раньше — отдаём существующую
        await db.rollback()
        existing = (await db.execute(
            select(Technique).where(func.lower(Technique.name) == name.lower())
        )).scalar_one_or_none()
        if existing:
            return existing
        raise
    await db.refresh(technique)
    return technique
