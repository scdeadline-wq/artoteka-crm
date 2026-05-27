from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Room, User
from app.schemas.room import RoomCreate, RoomDetailOut, RoomOut, RoomUpdate

router = APIRouter()


@router.get("/", response_model=list[RoomOut])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Room).order_by(Room.sort_order, Room.name)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/", response_model=RoomDetailOut, status_code=201)
async def create_room(
    body: RoomCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    room = Room(name=body.name.strip(), sort_order=body.sort_order)
    db.add(room)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Room with this name already exists")
    await db.refresh(room)
    return room


@router.put("/{room_id}/", response_model=RoomDetailOut)
async def update_room(
    room_id: int,
    body: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        room.name = data["name"].strip()
    if "sort_order" in data and data["sort_order"] is not None:
        room.sort_order = data["sort_order"]
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Room with this name already exists")
    await db.refresh(room)
    return room


@router.delete("/{room_id}/", status_code=200)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Удаление комнаты. Работы остаются в БД, room_id обнуляется (FK ON DELETE SET NULL)."""
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    await db.delete(room)
    await db.commit()
    return {"ok": True, "id": room_id}
