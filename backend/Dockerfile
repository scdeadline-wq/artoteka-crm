FROM python:3.13-slim

WORKDIR /app

# libpq-dev — для psycopg/asyncpg сборки.
# libpango-1.0-0 libpangoft2-1.0-0 — нативные зависимости weasyprint (PDF в /artworks/{id}/pdf).
# WeasyPrint >=53 не требует cairo и gdk-pixbuf — нужен только Pango.
# fonts-dejavu-core — шрифт для PDF.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
