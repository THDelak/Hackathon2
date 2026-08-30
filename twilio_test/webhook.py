"""Webhook temporal de Twilio, aislado de la integración oficial de Meta."""

from collections import OrderedDict
from threading import RLock
from typing import Callable
from urllib.parse import parse_qs
from xml.etree import ElementTree

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.agent import procesar_mensaje

router = APIRouter()
SAFE_ERROR = "No pude procesar el mensaje en este momento. Inténtalo de nuevo más tarde."
INVALID_REQUEST = "No pude interpretar el mensaje recibido."


class RecentMessageSids:
    """Deduplicación acotada en memoria, exclusiva del adaptador temporal."""

    def __init__(self, capacity: int = 1000):
        if capacity <= 0:
            raise ValueError("capacity debe ser mayor que cero.")
        self.capacity = capacity
        self._items: OrderedDict[str, str] = OrderedDict()
        self._lock = RLock()

    def claim(self, message_sid: str) -> bool:
        with self._lock:
            if message_sid in self._items:
                return False
            self._items[message_sid] = "processing"
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
            return True

    def complete(self, message_sid: str) -> None:
        with self._lock:
            if message_sid in self._items:
                self._items[message_sid] = "completed"

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


processed_message_sids = RecentMessageSids(capacity=1000)


def build_twiml(message: str | None = None) -> bytes:
    """Genera XML escapado; sin mensaje produce un ACK silencioso."""
    root = ElementTree.Element("Response")
    if message is not None:
        child = ElementTree.SubElement(root, "Message")
        child.text = message
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_twilio_form(raw_body: bytes) -> tuple[str, str, str] | None:
    """Extrae From, Body y MessageSid desde form-urlencoded."""
    try:
        fields = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    except (UnicodeDecodeError, ValueError):
        return None

    from_number = fields.get("From", [""])[0].strip()
    body = fields.get("Body", [""])[0].strip()
    message_sid = fields.get("MessageSid", [""])[0].strip()
    if not from_number or not body or not message_sid:
        return None
    return from_number, body, message_sid


def handle_twilio_webhook(
    raw_body: bytes,
    *,
    agent: Callable[[str, str], str] | None = None,
    message_sids: RecentMessageSids = processed_message_sids,
) -> bytes:
    parsed = parse_twilio_form(raw_body)
    if parsed is None:
        return build_twiml(INVALID_REQUEST)

    from_number, body, message_sid = parsed
    if not message_sids.claim(message_sid):
        return build_twiml()

    processor = agent or procesar_mensaje
    try:
        answer = processor(conversation_id=from_number, mensaje=body)
    except Exception:
        answer = SAFE_ERROR
    finally:
        message_sids.complete(message_sid)
    return build_twiml(answer)


@router.post("/twilio/webhook")
async def twilio_webhook(request: Request) -> Response:
    raw_body = await request.body()
    return Response(content=handle_twilio_webhook(raw_body), media_type="application/xml")
