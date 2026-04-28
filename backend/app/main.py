from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api import artworks, artists, techniques, auth, clients, sales, dashboard, import_airtable
from app.services.storage import get_image_bytes

app = FastAPI(
    title="Артотека",
    description="CRM для галерей и арт-дилеров",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://185.152.94.51"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(artworks.router, prefix="/artworks", tags=["artworks"])
app.include_router(artists.router, prefix="/artists", tags=["artists"])
app.include_router(techniques.router, prefix="/techniques", tags=["techniques"])
app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(sales.router, prefix="/sales", tags=["sales"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(import_airtable.router, prefix="/import", tags=["import"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/images/{path:path}")
async def serve_image(path: str):
    """Proxy images from MinIO storage."""
    data, content_type = get_image_bytes(path)
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
