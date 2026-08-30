"""API local mínima del inventario."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from app.agent import procesar_mensaje
from app.database import initialize_database
from app.memory import conversation_memory
from app.tools import listar_productos


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Hackathon 2 - Inventario", lifespan=lifespan)


class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    message: str

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conversation_id no puede estar vacío")
        return value.strip()


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
    return ChatResponse(response=procesar_mensaje(request.conversation_id, request.message))


@app.delete("/agent/conversations/{conversation_id}")
def clear_conversation(conversation_id: str) -> dict[str, bool]:
    return {"cleared": conversation_memory.clear(conversation_id)}
