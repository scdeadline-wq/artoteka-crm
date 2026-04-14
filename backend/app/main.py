from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import artworks, artists, techniques, auth, clients, sales, dashboard

app = FastAPI(
    title="Артотека",
    description="CRM для галерей и арт-дилеров",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.get("/health")
async def health():
    return {"status": "ok"}
