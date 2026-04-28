from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services.airtable import run_full_import

router = APIRouter()


@router.post("/airtable/")
async def import_airtable(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Импортирует все работы из Airtable «Список произведений искусства (П. Давтян)».

    Read-only. Скачивает фото и attachments в MinIO. Запуск занимает несколько минут.
    """
    return await run_full_import(db)
