"""Memoria conversacional en proceso, aislada por identificador."""

from collections import defaultdict
from contextlib import contextmanager
from threading import RLock
from typing import Iterator


class ConversationMemory:
    """Guarda los últimos turnos y sincroniza cada conversación por separado."""

    def __init__(self, max_turns: int = 10):
        if max_turns <= 0:
            raise ValueError("max_turns debe ser mayor que cero.")
        self.max_turns = max_turns
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._locks: defaultdict[str, RLock] = defaultdict(RLock)
        self._registry_lock = RLock()

    @contextmanager
    def conversation(self, conversation_id: str) -> Iterator[None]:
        """Serializa operaciones de una conversación sin bloquear las demás."""
        with self._registry_lock:
            lock = self._locks[conversation_id]
        with lock:
            yield

    def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Devuelve una copia serializable del historial en orden cronológico."""
        with self.conversation(conversation_id):
            return [message.copy() for message in self._histories.get(conversation_id, [])]

    def add_exchange(self, conversation_id: str, user: str, assistant: str) -> None:
        """Agrega un turno completo y recorta siempre por pares user/assistant."""
        with self.conversation(conversation_id):
            history = self._histories.setdefault(conversation_id, [])
            history.extend(
                [
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            )
            maximum_messages = self.max_turns * 2
            if len(history) > maximum_messages:
                del history[:-maximum_messages]

    def clear(self, conversation_id: str) -> bool:
        """Limpia una conversación y devuelve si contenía mensajes."""
        with self.conversation(conversation_id):
            return bool(self._histories.pop(conversation_id, None))

    def clear_all(self) -> None:
        """Limpia todas las conversaciones; útil para aislamiento de pruebas."""
        with self._registry_lock:
            self._histories.clear()


conversation_memory = ConversationMemory(max_turns=10)
