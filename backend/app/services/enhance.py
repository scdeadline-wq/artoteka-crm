"""Улучшение фото произведений: обрезка фона, баланс цвета, резкость."""
from io import BytesIO

from PIL import Image, ImageEnhance, ImageFilter


def auto_enhance(image_bytes: bytes) -> bytes:
    """Автоматическое улучшение фото: контраст, резкость, баланс белого."""
    img = Image.open(BytesIO(image_bytes))

    # Конвертируем в RGB если нужно
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 1. Авто-контраст
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)

    # 2. Немного насыщенности
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.1)

    # 3. Резкость
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=3))

    # 4. Яркость (чуть подтянуть если тёмное)
    from PIL import ImageStat
    stat = ImageStat.Stat(img)
    avg_brightness = sum(stat.mean[:3]) / 3
    if avg_brightness < 100:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def smart_crop(image_bytes: bytes) -> bytes:
    """Обрезка лишнего фона вокруг произведения.

    Находит границы произведения по контрасту с фоном и обрезает.
    """
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Найдём bounding box содержимого
    # Конвертируем в grayscale, определяем фоновый цвет по углам
    gray = img.convert("L")
    pixels = gray.load()
    w, h = gray.size

    # Средний цвет по углам (фон)
    corners = [
        pixels[0, 0], pixels[w - 1, 0],
        pixels[0, h - 1], pixels[w - 1, h - 1],
    ]
    bg_color = sum(corners) // len(corners)
    threshold = 30

    # Находим границы содержимого
    top, bottom, left, right = 0, h, 0, w

    # Сверху
    for y in range(h):
        row_diff = sum(1 for x in range(w) if abs(pixels[x, y] - bg_color) > threshold)
        if row_diff > w * 0.05:  # 5% пикселей отличаются от фона
            top = y
            break

    # Снизу
    for y in range(h - 1, -1, -1):
        row_diff = sum(1 for x in range(w) if abs(pixels[x, y] - bg_color) > threshold)
        if row_diff > w * 0.05:
            bottom = y + 1
            break

    # Слева
    for x in range(w):
        col_diff = sum(1 for y in range(h) if abs(pixels[x, y] - bg_color) > threshold)
        if col_diff > h * 0.05:
            left = x
            break

    # Справа
    for x in range(w - 1, -1, -1):
        col_diff = sum(1 for y in range(h) if abs(pixels[x, y] - bg_color) > threshold)
        if col_diff > h * 0.05:
            right = x + 1
            break

    # Добавляем небольшой padding (2%)
    pad_x = max(int((right - left) * 0.02), 5)
    pad_y = max(int((bottom - top) * 0.02), 5)
    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(w, right + pad_x)
    bottom = min(h, bottom + pad_y)

    # Обрезаем только если есть что обрезать (хотя бы 5% с какой-то стороны)
    min_crop = 0.05
    if (left / w > min_crop or top / h > min_crop or
            (w - right) / w > min_crop or (h - bottom) / h > min_crop):
        img = img.crop((left, top, right, bottom))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()
