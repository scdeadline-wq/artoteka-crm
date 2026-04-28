"""Импорт каталога из Airtable «Список произведений искусства (П. Давтян)».

Read-only: только GET-запросы. Никогда не пишем в Airtable.
"""
import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    Artwork,
    ArtworkStatus,
    Artist,
    Technique,
    Image,
    ArtworkAttachment,
    AttachmentKind,
)
from app.services.storage import upload_bytes

log = logging.getLogger(__name__)

AIRTABLE_API = "https://api.airtable.com/v0"

# Airtable field names (русские, как в базе)
F_NAME = "Имя"
F_PHOTOS = "Photos"
F_AUTHOR_LOOKUP = "Автора имя"
F_SIZE = "Размер"
F_TECHNIQUE = "Техника"
F_YEAR = "Год"
F_EXPERTISE = "Экспертиза"
F_FRAMING = "Обрамление"
F_PROVENANCE = "Провенанс/публикации/литература"
F_NOTE = "Примечание"
F_ARTIKUL = "Артикул"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.airtable_token}"}


async def fetch_all_records(table_id: str) -> list[dict]:
    records: list[dict] = []
    offset: str | None = None
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            params: dict[str, Any] = {"pageSize": 100}
            if offset:
                params["offset"] = offset
            r = await client.get(
                f"{AIRTABLE_API}/{settings.airtable_base_id}/{table_id}",
                headers=_headers(),
                params=params,
            )
            r.raise_for_status()
            data = r.json()
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
    return records


async def _download(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")


# === Парсеры ===

def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    s = re.sub(r"\s", "", str(value))
    m = re.search(r"(1[5-9]\d{2}|20\d{2}|21\d{2})", s)
    return int(m.group(1)) if m else None


_SIZE_RE = re.compile(r"(\d+(?:[,.]\d+)?)\s*[xхХ×*]\s*(\d+(?:[,.]\d+)?)", re.IGNORECASE)


def parse_size(value: Any) -> tuple[float | None, float | None]:
    if not value:
        return None, None
    m = _SIZE_RE.search(str(value))
    if not m:
        return None, None
    return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))


# === DB helpers ===

async def _get_or_create_artist(db: AsyncSession, name: str, cache: dict) -> Artist:
    if name in cache:
        return cache[name]
    existing = (await db.execute(select(Artist).where(Artist.name_ru == name))).scalar_one_or_none()
    if existing:
        cache[name] = existing
        return existing
    artist = Artist(name_ru=name)
    db.add(artist)
    await db.flush()
    cache[name] = artist
    return artist


async def _get_or_create_technique(db: AsyncSession, name: str, cache: dict) -> Technique:
    if name in cache:
        return cache[name]
    existing = (await db.execute(select(Technique).where(Technique.name == name))).scalar_one_or_none()
    if existing:
        cache[name] = existing
        return existing
    tech = Technique(name=name)
    db.add(tech)
    await db.flush()
    cache[name] = tech
    return tech


# === Импорт одной работы ===

async def _import_record(
    db: AsyncSession,
    record: dict,
    artist_cache: dict,
    technique_cache: dict,
    counters: dict,
) -> None:
    fields = record.get("fields", {})
    inventory = fields.get(F_ARTIKUL)
    if not inventory:
        counters["skipped_no_artikul"] += 1
        return

    author_names = fields.get(F_AUTHOR_LOOKUP, [])
    if author_names:
        artist_name = author_names[0]
    else:
        artist_name = "Неизвестный автор"
        counters["fallback_artist"] += 1
    artist = await _get_or_create_artist(db, artist_name, artist_cache)

    title = fields.get(F_NAME) or "Без названия"
    width, height = parse_size(fields.get(F_SIZE))
    year = parse_year(fields.get(F_YEAR))

    notes_parts = []
    if fields.get(F_PROVENANCE):
        notes_parts.append(f"Провенанс: {fields[F_PROVENANCE]}")
    if fields.get(F_NOTE):
        notes_parts.append(str(fields[F_NOTE]))
    notes = "\n\n".join(notes_parts) or None

    expertise = fields.get(F_EXPERTISE) or []
    framing = fields.get(F_FRAMING) or []

    technique_raw = fields.get(F_TECHNIQUE)
    techniques: list[Technique] = []
    if technique_raw:
        tech = await _get_or_create_technique(db, str(technique_raw).strip(), technique_cache)
        techniques.append(tech)

    artwork = Artwork(
        inventory_number=int(inventory),
        title=str(title),
        artist_id=artist.id,
        year=year,
        width_cm=width,
        height_cm=height,
        notes=notes,
        has_expertise=bool(expertise),
        status=ArtworkStatus.collection,
        techniques=techniques,
    )
    db.add(artwork)
    await db.flush()

    for idx, photo in enumerate(fields.get(F_PHOTOS) or []):
        url = photo.get("url")
        if not url:
            continue
        try:
            data, ctype = await _download(url)
            stored = upload_bytes(data, f"artworks/{artwork.id}", ctype, photo.get("filename"))
            db.add(Image(
                artwork_id=artwork.id,
                url=stored,
                is_primary=(idx == 0),
                sort_order=idx,
            ))
            counters["photos"] += 1
        except Exception as e:
            log.warning("Photo failed for artikul=%s: %s", inventory, e)
            counters["photo_errors"] += 1

    for kind, atts in ((AttachmentKind.expertise, expertise), (AttachmentKind.framing, framing)):
        for att in atts:
            url = att.get("url")
            if not url:
                continue
            try:
                data, ctype = await _download(url)
                stored = upload_bytes(data, f"attachments/{artwork.id}/{kind.value}", ctype, att.get("filename"))
                db.add(ArtworkAttachment(
                    artwork_id=artwork.id,
                    kind=kind,
                    url=stored,
                    filename=att.get("filename"),
                ))
                counters[f"{kind.value}_files"] += 1
            except Exception as e:
                log.warning("Attachment %s failed for artikul=%s: %s", kind.value, inventory, e)
                counters["attachment_errors"] += 1

    counters["artworks"] += 1


async def run_full_import(db: AsyncSession) -> dict:
    """Импорт всех работ из Airtable. Возвращает счётчики."""
    if not settings.airtable_token:
        raise RuntimeError("AIRTABLE_TOKEN is not set")

    log.info("Fetching Airtable records...")
    records = await fetch_all_records(settings.airtable_artworks_table)
    log.info("Got %d records, importing...", len(records))

    artist_cache: dict[str, Artist] = {}
    technique_cache: dict[str, Technique] = {}
    counters = {
        "total": len(records),
        "artworks": 0,
        "photos": 0,
        "photo_errors": 0,
        "expertise_files": 0,
        "framing_files": 0,
        "attachment_errors": 0,
        "skipped_no_artikul": 0,
        "fallback_artist": 0,
    }

    for i, rec in enumerate(records, 1):
        try:
            await _import_record(db, rec, artist_cache, technique_cache, counters)
        except Exception as e:
            log.exception("Record %s failed: %s", rec.get("id"), e)
            counters.setdefault("record_errors", 0)
            counters["record_errors"] += 1
        if i % 20 == 0:
            await db.commit()
            log.info("Imported %d/%d", i, len(records))

    await db.commit()
    counters["artists_created"] = len(artist_cache)
    counters["techniques_seen"] = len(technique_cache)
    log.info("Import done: %s", counters)
    return counters
