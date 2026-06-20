from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import runs, settings as settings_router, sse, uploads
from app.core.settings import settings
from app.core.workspace import init_workspace


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_workspace()
    yield


app = FastAPI(
    title="Pixpilot API",
    description="AI-assisted product image & copy generation pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(settings_router.router)
app.include_router(sse.router)
app.include_router(uploads.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
