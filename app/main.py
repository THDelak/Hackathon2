"""API local mínima del inventario."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import initialize_database
from app.tools import listar_productos


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Hackathon 2 - Inventario", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/productos")
def productos() -> list[dict]:
    return listar_productos()
