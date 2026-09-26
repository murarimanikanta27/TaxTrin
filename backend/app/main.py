"""TaxTrin API entrypoint.

Run with: uvicorn app.main:app --reload --port 8000 (from backend/, inside
the venv). See README.md for full setup instructions.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import admin, auth, clients, etax_export, payroll, returns, td4

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # POC convenience: auto-create tables if they don't exist yet. A real
    # deployment would rely on an Alembic migration instead of this.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0-poc",
    description=(
        "TaxTrin Trinidad & Tobago tax preparation POC API. "
        "See /docs for interactive API exploration."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Export-Log-Id", "X-Validation-Status", "Content-Disposition"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(admin.router)
app.include_router(td4.router)
app.include_router(returns.router)
app.include_router(payroll.router)
app.include_router(etax_export.router)
