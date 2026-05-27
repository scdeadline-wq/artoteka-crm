"""CRUD пользователей.

Правила:
- Видеть/создавать/удалять может только admin (owner+admin).
- Назначать/снимать роль owner может ТОЛЬКО owner.
- Удалять owner может ТОЛЬКО owner; нельзя удалить последнего owner.
- Нельзя удалить самого себя.
- Email — уникальный.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, is_owner, require_admin
from app.database import get_db
from app.models import User, UserRole
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter()


def _check_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Некорректный email")
    return email


async def _count_owners(db: AsyncSession) -> int:
    return (await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.owner)
    )).scalar_one()


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(User).order_by(User.role, User.name)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if body.role == UserRole.owner and not is_owner(actor):
        raise HTTPException(status_code=403, detail="Только owner может назначать роль owner")
    email = _check_email(body.email)
    user = User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже есть")
    await db.refresh(user)
    return user


@router.put("/{user_id}/", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = body.model_dump(exclude_unset=True)
    new_role: UserRole | None = data.get("role")

    # Только owner может трогать owner-ов или ставить роль owner.
    if user.role == UserRole.owner and not is_owner(actor):
        raise HTTPException(status_code=403, detail="Менять owner может только owner")
    if new_role == UserRole.owner and not is_owner(actor):
        raise HTTPException(status_code=403, detail="Назначать owner может только owner")

    # Защита от потери последнего owner.
    if user.role == UserRole.owner and new_role and new_role != UserRole.owner:
        if (await _count_owners(db)) <= 1:
            raise HTTPException(status_code=400, detail="Нельзя снять роль с последнего owner")

    if "name" in data and data["name"] is not None:
        user.name = data["name"].strip()
    if "role" in data and data["role"] is not None:
        user.role = data["role"]
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data["password"])

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}/", status_code=200)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if user_id == actor.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.owner:
        if not is_owner(actor):
            raise HTTPException(status_code=403, detail="Удалять owner может только owner")
        if (await _count_owners(db)) <= 1:
            raise HTTPException(status_code=400, detail="Нельзя удалить последнего owner")
    await db.delete(user)
    await db.commit()
    return {"ok": True, "id": user_id}
