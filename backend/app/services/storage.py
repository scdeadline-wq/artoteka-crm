import uuid
from io import BytesIO

import boto3
from fastapi import UploadFile

from app.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


async def upload_image(file: UploadFile, artwork_id: int) -> str:
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    key = f"artworks/{artwork_id}/{uuid.uuid4().hex}.{ext}"
    content = await file.read()

    client = _get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content,
        ContentType=file.content_type or "image/jpeg",
    )
    # Return relative path — served via /images/ proxy endpoint
    return f"/images/{key}"


def delete_object(key: str) -> None:
    """Удалить объект из S3 по key. Отсутствующий key — не ошибка."""
    client = _get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket, Key=key)


def get_image_bytes(key: str) -> tuple[bytes, str]:
    """Download image from S3 by key. Returns (bytes, content_type)."""
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read(), response.get("ContentType", "image/jpeg")


def get_or_make_thumbnail(key: str, width: int) -> tuple[bytes, str]:
    """Уменьшенная копия картинки шириной ~width (JPEG). Кэшируется в MinIO под
    thumbs/w{width}/{key} — ресайз делается один раз на (картинку, ширину).
    Для каталога это в разы меньше байт, чем оригинал. На не-картинке/ошибке
    тихо отдаём оригинал. ВАЖНО: PIL — блокирующий, вызывать через asyncio.to_thread."""
    from PIL import Image as PILImage, ImageOps

    width = max(50, min(int(width), 1600))
    thumb_key = f"thumbs/w{width}/{key}"
    client = _get_s3_client()

    # 1) готовое превью из кэша
    try:
        resp = client.get_object(Bucket=settings.s3_bucket, Key=thumb_key)
        return resp["Body"].read(), resp.get("ContentType", "image/jpeg")
    except Exception:
        pass

    # 2) оригинал (если нет — пусть пробрасывается ClientError → 404 в эндпоинте)
    resp = client.get_object(Bucket=settings.s3_bucket, Key=key)
    original = resp["Body"].read()
    original_ct = resp.get("ContentType", "image/jpeg")

    # 3) ресайз
    try:
        img = PILImage.open(BytesIO(original))
        img = ImageOps.exif_transpose(img)  # учесть поворот с телефона
        if img.width <= width:
            return original, original_ct  # уже мельче запрошенного — отдаём как есть
        ratio = width / img.width
        img = img.resize((width, max(1, int(img.height * ratio))), PILImage.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=80, optimize=True)
        data = out.getvalue()
    except Exception:
        return original, original_ct  # не картинка/битый файл → оригинал

    # 4) кладём в кэш (сбой кэша не критичен)
    try:
        client.put_object(Bucket=settings.s3_bucket, Key=thumb_key, Body=data, ContentType="image/jpeg")
    except Exception:
        pass
    return data, "image/jpeg"


_EXT_BY_CTYPE = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
    "application/pdf": "pdf",
}


def upload_bytes(data: bytes, prefix: str, content_type: str, filename: str | None = None) -> str:
    """Положить bytes в MinIO под `{prefix}/{uuid}.{ext}`. Возвращает /images/-путь."""
    ext = _EXT_BY_CTYPE.get(content_type.split(";")[0].strip().lower())
    if not ext and filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
    if not ext:
        ext = "bin"
    key = f"{prefix.strip('/')}/{uuid.uuid4().hex}.{ext}"
    client = _get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"/images/{key}"
