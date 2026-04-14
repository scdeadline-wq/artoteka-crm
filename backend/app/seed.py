"""Начальное наполнение справочников."""
import asyncio

from sqlalchemy import select
from app.database import engine, async_session, Base
from app.models import Technique, User, UserRole
from passlib.hash import bcrypt

TECHNIQUES = [
    # Живопись
    ("Холст, масло", "Живопись"),
    ("Картон, масло", "Живопись"),
    ("Дерево, масло", "Живопись"),
    ("Холст, темпера", "Живопись"),
    ("Холст, акрил", "Живопись"),
    ("Холст, смешанная техника", "Живопись"),
    # Графика
    ("Бумага, графитный карандаш", "Графика"),
    ("Бумага, тушь", "Графика"),
    ("Бумага, тушь, перо", "Графика"),
    ("Бумага, акварель", "Графика"),
    ("Бумага, гуашь", "Графика"),
    ("Бумага, пастель", "Графика"),
    ("Бумага, сангина", "Графика"),
    ("Бумага, соус", "Графика"),
    ("Бумага, уголь", "Графика"),
    ("Бумага, цветные карандаши", "Графика"),
    ("Бумага, смешанная техника", "Графика"),
    # Печатная графика
    ("Литография", "Печатная графика"),
    ("Офорт", "Печатная графика"),
    ("Ксилография", "Печатная графика"),
    ("Линогравюра", "Печатная графика"),
    ("Шелкография (сериграфия)", "Печатная графика"),
    # Скульптура
    ("Бронза", "Скульптура"),
    ("Керамика", "Скульптура"),
    ("Фарфор", "Скульптура"),
    ("Дерево", "Скульптура"),
    ("Гипс", "Скульптура"),
    # Декоративно-прикладное
    ("Фарфор, роспись", "ДПИ"),
    ("Стекло", "ДПИ"),
    ("Эмаль", "ДПИ"),
    ("Текстиль", "ДПИ"),
    # Фотография
    ("Фотография, серебряно-желатиновая печать", "Фотография"),
    ("Фотография, цифровая печать", "Фотография"),
    # Прочее
    ("Смешанная техника", "Прочее"),
    ("Коллаж", "Прочее"),
    ("Инсталляция", "Прочее"),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Техники
        existing = (await session.execute(select(Technique))).scalars().all()
        existing_names = {t.name for t in existing}
        for name, category in TECHNIQUES:
            if name not in existing_names:
                session.add(Technique(name=name, category=category))

        # Пользователь по умолчанию (Паруер — owner)
        existing_user = (await session.execute(
            select(User).where(User.email == "paruer@artoteka.ru")
        )).scalar_one_or_none()
        if not existing_user:
            session.add(User(
                name="Паруер",
                email="paruer@artoteka.ru",
                password_hash=bcrypt.hash("artoteka2026"),
                role=UserRole.owner,
            ))

        await session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
