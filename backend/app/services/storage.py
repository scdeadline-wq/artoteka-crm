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


def get_image_bytes(key: str) -> tuple[bytes, str]:
    """Download image from S3 by key. Returns (bytes, content_type)."""
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read(), response.get("ContentType", "image/jpeg")


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
