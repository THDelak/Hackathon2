from fastapi.testclient import TestClient

from app.main import app
from app.memory import conversation_memory


client = TestClient(app)


def test_reset_conversation_endpoint_es_aislado():
    conversation_memory.clear_all()
    conversation_memory.add_exchange("a", "Pregunta A", "Respuesta A")
    conversation_memory.add_exchange("b", "Pregunta B", "Respuesta B")

    response = client.delete("/agent/conversations/a")
    assert response.status_code == 200
    assert response.json() == {"cleared": True}
    assert conversation_memory.get_history("a") == []
    assert conversation_memory.get_history("b") != []

    second_response = client.delete("/agent/conversations/a")
    assert second_response.json() == {"cleared": False}


def test_chat_rechaza_conversation_id_vacio():
    response = client.post("/agent/chat", json={"conversation_id": "   ", "message": "Hola"})
    assert response.status_code == 422
