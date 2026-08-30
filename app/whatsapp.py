"""Adaptador de entrada y salida para WhatsApp Cloud API."""

import os
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable

import httpx

from app.agent import procesar_mensaje

DEFAULT_API_VERSION = "v23.0"
SEND_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class IncomingTextMessage:
    sender: str
    message_id: str
    body: str


@dataclass(frozen=True)
class SendResult:
    success: bool
    error: str = ""


class RecentMessageIds:
    """Registro idempotente acotado y seguro para un único proceso."""

    def __init__(self, capacity: int = 1000):
        if capacity <= 0:
            raise ValueError("capacity debe ser mayor que cero.")
        self.capacity = capacity
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._lock = RLock()

    def claim(self, message_id: str) -> bool:
        """Reserva un ID; devuelve False si ya había sido procesado."""
        with self._lock:
            if message_id in self._ids:
                return False
            self._ids[message_id] = None
            while len(self._ids) > self.capacity:
                self._ids.popitem(last=False)
            return True

    def clear(self) -> None:
        with self._lock:
            self._ids.clear()


processed_message_ids = RecentMessageIds(capacity=1000)


def parse_webhook_payload(payload: Any) -> list[IncomingTextMessage]:
    """Extrae únicamente mensajes de texto completos de un payload de Meta."""
    if not isinstance(payload, dict) or not isinstance(payload.get("entry"), list):
        return []

    extracted: list[IncomingTextMessage] = []
    for entry in payload["entry"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("changes"), list):
            continue
        for change in entry["changes"]:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict) or not isinstance(value.get("messages"), list):
                continue
            for message in value["messages"]:
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                text = message.get("text")
                sender = message.get("from")
                message_id = message.get("id")
                body = text.get("body") if isinstance(text, dict) else None
                if all(isinstance(item, str) and item.strip() for item in (sender, message_id, body)):
                    extracted.append(
                        IncomingTextMessage(sender.strip(), message_id.strip(), body.strip())
                    )
    return extracted


def send_whatsapp_message(to: str, message: str, *, client: Any = httpx) -> SendResult:
    """Envía texto mediante Graph API sin propagar detalles sensibles."""
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    api_version = os.getenv("WHATSAPP_API_VERSION", DEFAULT_API_VERSION).strip() or DEFAULT_API_VERSION
    if not access_token or not phone_number_id:
        return SendResult(False, "WhatsApp no está configurado.")

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        response = client.post(
            url,
            headers=headers,
            json=payload,
            timeout=SEND_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return SendResult(True)
    except Exception:
        return SendResult(False, "No fue posible enviar la respuesta por WhatsApp.")


def handle_webhook_payload(
    payload: Any,
    *,
    agent: Callable[[str, str], str] = procesar_mensaje,
    sender: Callable[[str, str], SendResult] = send_whatsapp_message,
    message_ids: RecentMessageIds = processed_message_ids,
) -> None:
    """Procesa textos nuevos sin convertir fallos de salida en errores del webhook."""
    for incoming in parse_webhook_payload(payload):
        if not message_ids.claim(incoming.message_id):
            continue
        response = agent(incoming.sender, incoming.body)
        sender(incoming.sender, response)
