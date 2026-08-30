from urllib.parse import urlencode
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from twilio_test import webhook
from twilio_test.app import app
from twilio_test.webhook import RecentMessageSids, build_twiml, handle_twilio_webhook, parse_twilio_form


client = TestClient(app)


def form_data(
    *,
    from_number="whatsapp:+5215550000000",
    body="¿Cuántas camisetas negras tenemos?",
    message_sid="SM123",
):
    return urlencode({"From": from_number, "Body": body, "MessageSid": message_sid}).encode()


def xml_message(content: bytes) -> str | None:
    return ElementTree.fromstring(content).findtext("Message")


def test_parse_form_extrae_from_body_y_message_sid():
    assert parse_twilio_form(form_data()) == (
        "whatsapp:+5215550000000",
        "¿Cuántas camisetas negras tenemos?",
        "SM123",
    )


def test_webhook_form_extrae_campos_y_usa_from_como_conversation_id(monkeypatch):
    calls = []

    def fake_agent(*, conversation_id, mensaje):
        calls.append((conversation_id, mensaje))
        return "Hay 10 camisetas negras."

    monkeypatch.setattr(webhook, "procesar_mensaje", fake_agent)
    webhook.processed_message_sids.clear()
    response = client.post(
        "/twilio/webhook",
        content=form_data(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert calls == [("whatsapp:+5215550000000", "¿Cuántas camisetas negras tenemos?")]
    assert xml_message(response.content) == "Hay 10 camisetas negras."


def test_twiml_escapa_caracteres_especiales():
    content = build_twiml('Stock < 10 & nombre "Camiseta" > prueba')
    assert xml_message(content) == 'Stock < 10 & nombre "Camiseta" > prueba'
    assert b"&lt;" in content and b"&amp;" in content and b"&gt;" in content


def test_acentos_enye_y_signos_se_conservan():
    calls = []
    answer = handle_twilio_webhook(
        form_data(body="¿Añadimos 2 camisetas mañana?"),
        agent=lambda **kwargs: calls.append(kwargs) or "Sí, operación válida: niño.",
        message_sids=RecentMessageSids(),
    )
    assert calls[0]["mensaje"] == "¿Añadimos 2 camisetas mañana?"
    assert xml_message(answer) == "Sí, operación válida: niño."


@pytest.mark.parametrize(
    "fields",
    [
        {"Body": "Hola", "MessageSid": "SM1"},
        {"From": "whatsapp:+521", "MessageSid": "SM1"},
        {"From": "whatsapp:+521", "Body": "Hola"},
        {"From": "whatsapp:+521", "Body": "   ", "MessageSid": "SM1"},
    ],
)
def test_campos_faltantes_o_body_vacio_se_controlan(fields):
    calls = []
    result = handle_twilio_webhook(
        urlencode(fields).encode(),
        agent=lambda **kwargs: calls.append(kwargs) or "No debe ejecutarse",
        message_sids=RecentMessageSids(),
    )
    assert xml_message(result) == webhook.INVALID_REQUEST
    assert calls == []


def test_payload_malformado_se_controla():
    result = handle_twilio_webhook(b"\xff\xfe", message_sids=RecentMessageSids())
    assert xml_message(result) == webhook.INVALID_REQUEST


def test_message_sid_duplicado_no_llama_dos_veces_al_agente():
    calls = []
    ids = RecentMessageSids()
    agent = lambda **kwargs: calls.append(kwargs) or "Venta registrada"
    first = handle_twilio_webhook(form_data(body="Vende 2"), agent=agent, message_sids=ids)
    duplicate = handle_twilio_webhook(form_data(body="Vende 2"), agent=agent, message_sids=ids)

    assert xml_message(first) == "Venta registrada"
    assert xml_message(duplicate) is None
    assert len(calls) == 1


def test_remitentes_diferentes_no_comparten_conversation_id():
    calls = []
    ids = RecentMessageSids()
    agent = lambda **kwargs: calls.append(kwargs) or "OK"
    handle_twilio_webhook(form_data(from_number="whatsapp:+521111", message_sid="SMA"), agent=agent, message_sids=ids)
    handle_twilio_webhook(form_data(from_number="whatsapp:+521222", message_sid="SMB"), agent=agent, message_sids=ids)
    assert [call["conversation_id"] for call in calls] == ["whatsapp:+521111", "whatsapp:+521222"]


def test_excepcion_del_agente_no_expone_secretos_y_el_duplicado_no_reintenta():
    calls = []
    ids = RecentMessageSids()

    def failing_agent(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("GROQ_API_KEY=secreto-que-no-debe-salir")

    first = handle_twilio_webhook(form_data(), agent=failing_agent, message_sids=ids)
    duplicate = handle_twilio_webhook(form_data(), agent=failing_agent, message_sids=ids)
    assert xml_message(first) == webhook.SAFE_ERROR
    assert b"secreto-que-no-debe-salir" not in first
    assert xml_message(duplicate) is None
    assert len(calls) == 1


def test_registro_de_sids_es_acotado():
    ids = RecentMessageSids(capacity=2)
    assert ids.claim("SM1") is True
    assert ids.claim("SM2") is True
    assert ids.claim("SM3") is True
    assert ids.claim("SM2") is False
    assert ids.claim("SM1") is True


def test_app_temporal_conserva_endpoints_oficiales_y_agrega_twilio():
    paths = set(app.openapi()["paths"])
    assert {"/health", "/productos", "/agent/chat", "/webhook", "/twilio/webhook"} <= paths
