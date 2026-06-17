from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api import artworks, artists, techniques, auth, clients, sales, dashboard, import_airtable, rooms, users, settings as settings_api, storage
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
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(storage.router, prefix="/storage", tags=["storage"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(settings_api.router, prefix="/settings", tags=["settings"])
app.include_router(import_airtable.router, prefix="/import", tags=["import"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/images/{path:path}")
async def serve_image(path: str):
    """Proxy images from MinIO storage."""
    try:
        data, content_type = get_image_bytes(path)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404", "NoSuchBucket"):
            raise HTTPException(status_code=404, detail="Image not found")
        raise
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
