FROM python:3.13-slim

WORKDIR /app

# libpq-dev — для psycopg/asyncpg сборки.
# libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 — нативные зависимости weasyprint
# (нужны для рендера PDF в /artworks/{id}/pdf).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf2.0-0 \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
