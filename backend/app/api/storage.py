from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import User
from app.models.storage import StorageOption, STORAGE_KINDS
from app.schemas.storage import StorageOptionCreate, StorageOptionOut, StorageOptionUpdate

router = APIRouter()


def _check_kind(kind: str) -> None:
    if kind not in STORAGE_KINDS:
        raise HTTPException(
            status_code=422,
            detail=f"Недопустимый вид хранения «{kind}». Допустимые: {', '.join(STORAGE_KINDS)}",
        )


@router.get("/", response_model=list[StorageOptionOut])
async def list_storage(
    kind: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(StorageOption).order_by(StorageOption.kind, StorageOption.sort_order, StorageOption.name)
    if kind:
        _check_kind(kind)
        stmt = stmt.where(StorageOption.kind == kind)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/", response_model=StorageOptionOut, status_code=201)
async def create_storage(
    body: StorageOptionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    _check_kind(body.kind)
    opt = StorageOption(kind=body.kind, name=body.name.strip(), sort_order=body.sort_order)
    db.add(opt)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Такое место уже есть в этом списке")
    await db.refresh(opt)
    return opt


@router.put("/{option_id}/", response_model=StorageOptionOut)
async def update_storage(
    option_id: int,
    body: StorageOptionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    opt = await db.get(StorageOption, option_id)
    if not opt:
        raise HTTPException(status_code=404, detail="Storage option not found")
    data = body.model_dump(exclude_unset=True)
    if data.get("name") is not None:
        opt.name = data["name"].strip()
    if data.get("sort_order") is not None:
        opt.sort_order = data["sort_order"]
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Такое место уже есть в этом списке")
    await db.refresh(opt)
    return opt


@router.delete("/{option_id}/", status_code=200)
async def delete_storage(
    option_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Удаление места. Работы остаются, ссылка обнуляется (FK ON DELETE SET NULL)."""
    opt = await db.get(StorageOption, option_id)
    if not opt:
        raise HTTPException(status_code=404, detail="Storage option not found")
    await db.delete(opt)
    await db.commit()
    return {"ok": True, "id": option_id}
