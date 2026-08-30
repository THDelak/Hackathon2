"""API local mínima del inventario."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import procesar_mensaje
from app.database import initialize_database
from app.tools import listar_productos


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Hackathon 2 - Inventario", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/productos")
def productos() -> list[dict]:
    return listar_productos()


@app.post("/agent/chat", response_model=ChatResponse)
def agent_chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(response=procesar_mensaje(request.message))
