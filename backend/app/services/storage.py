import uuid

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
    return f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"
