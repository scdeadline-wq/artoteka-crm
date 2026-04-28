import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.auth import get_current_user
from app.models import Artist, User
from app.schemas.artist import ArtistCreate, ArtistUpdate, ArtistOut

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/", response_model=list[ArtistOut])
async def list_artists(
    q: str | None = None,
    is_group: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Artist).order_by(Artist.name_ru)
    if q:
        stmt = stmt.where(Artist.name_ru.ilike(f"%{q}%") | Artist.name_en.ilike(f"%{q}%"))
    if is_group is not None:
        stmt = stmt.where(Artist.is_group == is_group)
    return (await db.execute(stmt)).scalars().all()


@router.post("/", response_model=ArtistOut, status_code=201)
async def create_artist(
    body: ArtistCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = Artist(**body.model_dump())
    db.add(artist)
    await db.commit()
    await db.refresh(artist)
    return artist


@router.get("/{artist_id}/", response_model=ArtistOut)
async def get_artist(
    artist_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist


@router.put("/{artist_id}/", response_model=ArtistOut)
async def update_artist(
    artist_id: int,
    body: ArtistUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(artist, key, value)
    await db.commit()
    await db.refresh(artist)
    return artist


TRANSLATE_PROMPT = """Ты переводишь имена художников с русского на английский для каталога галереи.

Правила:
- Известный художник (есть в Wikipedia) → официальное английское имя как в Wikipedia (например «Дмитрий Пригов» → «Dmitri Prigov», «Пабло Пикассо» → «Pablo Picasso», «Виктор Пивоваров» → «Viktor Pivovarov»).
- Малоизвестный → стандартная транслитерация (BGN/PCGN). Русские отчества опускай.
- Уже на латинице (например «Dariel D.») → возвращай как есть.
- Скобки сохраняй: «Алексей Смирнов (фон Раух)» → «Aleksey Smirnov (von Rauch)».
- Запись с запятой (группа авторов) — переводи каждое имя, запятую сохрани: «Andrey Monastyrsky, Vladimir Zakharov».
- «Неизвестный автор» → «Unknown artist».
- НЕ выдумывай. Если не уверен в Wikipedia-варианте — просто транслитерируй.

Верни ТОЛЬКО JSON-массив (никаких комментариев и markdown):
[{"id": 1, "name_en": "..."}, ...]
"""


async def _translate_batch(items: list[dict]) -> list[dict]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": TRANSLATE_PROMPT},
                    {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
                ],
                "max_tokens": 4000,
            },
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(content)


BIO_PROMPT = """Ты заполняешь биографии художников для каталога галереи.

Я дам JSON с русским и английским именем. Для каждого художника верни биографию на русском.

Что писать:
- Годы жизни / даты рождения
- Учебное заведение, школа, направление
- Стиль / творческая манера
- Известные работы, выставки, музейные коллекции, награды
- Связи с другими художниками или арт-движениями

Когда писать:
- Если знаешь хотя бы 2-3 КОНКРЕТНЫХ факта — пиши, даже коротко (2-3 предложения), это полезно для каталога.
- Если ничего конкретного не знаешь и пришлось бы выдумывать — bio: null.

Чего НЕ делать:
- НЕ выдумывай конкретные даты, названия работ, биографические факты.
- НЕ пиши «возможно», «вероятно», «по некоторым данным», «(предположительно)».
- НЕ пиши воду без конкретики: «известный художник», «талантливый мастер», «значимый автор».
- НЕ повторяй имя в начале bio.

Верни ТОЛЬКО JSON-массив (никакого markdown):
[{"id": 1, "bio": "..."}, {"id": 2, "bio": null}, ...]
"""

ENRICH_BIO_PROMPT = """Ты заполняешь биографии художников по результатам веб-поиска.

Тебе дадут JSON: для каждого художника — имя и сниппеты (заголовок + текст) из поисковика.
На основе этих сниппетов напиши биографию на русском (2-4 предложения):
- Годы жизни / годы творчества
- Школа, направление, стиль
- Известные работы, выставки, коллекции
- Связи с движениями

Правила:
- Опирайся ТОЛЬКО на сниппеты. Не добавляй фактов от себя.
- Если в сниппетах нет информации о конкретном художнике (поиск нашёл что-то другое) — bio: null.
- Если сниппеты противоречат друг другу — выбирай согласованную версию или null.
- Не пиши «согласно поиску», «по данным интернета», «возможно».
- Не повторяй имя в начале bio.

Верни ТОЛЬКО JSON-массив:
[{"id": 1, "bio": "..."}, {"id": 2, "bio": null}, ...]
"""


async def _fill_bio_batch(items: list[dict]) -> list[dict]:
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": BIO_PROMPT},
                    {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
                ],
                "max_tokens": 6000,
            },
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(content)


@router.post("/fill-bios/")
async def fill_bios(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Заполняет bio через Claude у всех артистов с пустым bio."""
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=500, detail="OpenRouter not configured")

    artists = (await db.execute(
        select(Artist).where(or_(Artist.bio.is_(None), Artist.bio == ""))
    )).scalars().all()

    if not artists:
        return {"updated": 0, "skipped_unknown": 0, "total_pending": 0}

    by_id = {a.id: a for a in artists}
    items = [
        {"id": a.id, "name_ru": a.name_ru, "name_en": a.name_en or None}
        for a in artists
    ]

    updated = 0
    skipped = 0
    BATCH = 20
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        try:
            results = await _fill_bio_batch(batch)
        except Exception as e:
            log.exception("bio batch failed: %s", e)
            continue
        for r in results:
            artist = by_id.get(r.get("id"))
            if not artist:
                continue
            bio = r.get("bio")
            if bio:
                artist.bio = bio.strip()
                updated += 1
            else:
                skipped += 1
        await db.commit()

    return {
        "updated": updated,
        "skipped_unknown": skipped,
        "total_pending": len(items),
    }


SEARCHAPI_TEXT_URL = "https://www.searchapi.io/api/v1/search"


async def _text_search(query: str) -> list[dict]:
    """Поиск в Google через SearchAPI.io. Возвращает organic_results (top 5)."""
    if not settings.searchapi_key:
        return []
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(
                SEARCHAPI_TEXT_URL,
                params={
                    "engine": "google",
                    "q": query,
                    "api_key": settings.searchapi_key,
                    "num": 5,
                },
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("text search failed for %r: %s", query, e)
            return []
    return [
        {"title": x.get("title"), "snippet": x.get("snippet"), "source": x.get("displayed_link")}
        for x in (data.get("organic_results") or [])[:5]
    ]


async def _search_artist_snippets(artist: Artist) -> list[dict]:
    """Сниппеты для одного артиста: имя + 'художник биография'."""
    name = artist.name_ru.strip()
    return await _text_search(f"{name} художник биография")


@router.post("/enrich-bios-with-search/")
async def enrich_bios_with_search(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Для всех артистов с пустым bio: делает Google-поиск, отдаёт сниппеты Claude."""
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=500, detail="OpenRouter not configured")
    if not settings.searchapi_key:
        raise HTTPException(status_code=500, detail="SearchAPI not configured")

    artists = (await db.execute(
        select(Artist).where(or_(Artist.bio.is_(None), Artist.bio == ""))
    )).scalars().all()
    if not artists:
        return {"updated": 0, "no_results": 0, "total_pending": 0}

    # Параллельный поиск (по 5 одновременно)
    import asyncio
    semaphore = asyncio.Semaphore(5)

    async def fetch(a: Artist) -> tuple[Artist, list[dict]]:
        async with semaphore:
            return a, await _search_artist_snippets(a)

    pairs = await asyncio.gather(*(fetch(a) for a in artists))

    # В Claude отправляем только тех, для кого есть сниппеты
    items = []
    no_results = 0
    for artist, snippets in pairs:
        if not snippets:
            no_results += 1
            continue
        items.append({
            "id": artist.id,
            "name_ru": artist.name_ru,
            "name_en": artist.name_en,
            "snippets": snippets,
        })

    by_id = {a.id: a for a in artists}
    updated = 0
    BATCH = 10
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        try:
            async with httpx.AsyncClient(timeout=240.0) as client:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.ai_model,
                        "messages": [
                            {"role": "system", "content": ENRICH_BIO_PROMPT},
                            {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
                        ],
                        "max_tokens": 6000,
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            results = json.loads(content)
        except Exception as e:
            log.exception("enrich batch failed: %s", e)
            continue
        for r in results:
            artist = by_id.get(r.get("id"))
            bio = (r.get("bio") or "").strip()
            if artist and bio:
                artist.bio = bio
                updated += 1
        await db.commit()

    return {
        "updated": updated,
        "no_results": no_results,
        "total_pending": len(artists),
        "snippets_found": len(items),
    }


@router.post("/translate-names/")
async def translate_names(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Заполняет name_en у всех артистов с пустым английским именем (через Claude)."""
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=500, detail="OpenRouter not configured")

    artists = (await db.execute(
        select(Artist).where(or_(Artist.name_en.is_(None), Artist.name_en == ""))
    )).scalars().all()

    if not artists:
        return {"updated": 0, "total_pending": 0}

    by_id = {a.id: a for a in artists}
    items = [{"id": a.id, "name_ru": a.name_ru} for a in artists]

    updated = 0
    BATCH = 30
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        try:
            results = await _translate_batch(batch)
        except Exception as e:
            log.exception("translate batch failed: %s", e)
            continue
        for r in results:
            artist = by_id.get(r.get("id"))
            name_en = (r.get("name_en") or "").strip()
            if artist and name_en:
                artist.name_en = name_en
                updated += 1
        await db.commit()

    return {"updated": updated, "total_pending": len(items)}
