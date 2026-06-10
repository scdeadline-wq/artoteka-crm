from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import User
from app.services.airtable import run_full_import

router = APIRouter()


@router.post("/airtable/")
async def import_airtable(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """Импортирует все работы из Airtable «Список произведений искусства (П. Давтян)».

    Read-only. Скачивает фото и attachments в MinIO. Запуск занимает несколько минут.
    Только admin.
    """
    return await run_full_import(db)
