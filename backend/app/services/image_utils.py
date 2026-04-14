"""Утилиты для работы с изображениями: конвертация форматов, нормализация."""
from io import BytesIO

from PIL import Image

# Регистрируем HEIF/HEIC поддержку при импорте
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


def normalize_image(image_bytes: bytes) -> bytes:
    """Конвертирует любой формат (HEIC, WEBP, PNG, TIFF) в JPEG.

    Также исправляет ориентацию по EXIF.
    """
    img = Image.open(BytesIO(image_bytes))

    # Исправляем ориентацию по EXIF
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Конвертируем в RGB (убираем альфа-канал если есть)
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
