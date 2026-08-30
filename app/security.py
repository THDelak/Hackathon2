"""Controles deterministas de entrada y salida para el agente."""

import os
import re
import unicodedata
from dataclasses import dataclass


SAFE_REJECTION = (
    "No puedo ayudar con instrucciones para revelar secretos o modificar el sistema "
    "fuera de las operaciones permitidas de inventario."
)
SAFE_OUTPUT_REJECTION = "La respuesta fue bloqueada porque podría contener información sensible."


@dataclass(frozen=True)
class SecurityResult:
    allowed: bool
    reason: str = ""
    category: str = "allowed"


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


INPUT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "internal_instructions",
        (
            r"\b(system prompt|prompt del sistema|instrucciones internas|developer message)\b",
            r"\b(revela|muestra|dime|show|reveal|repeat|imprime)\b.{0,50}\b(prompt|instrucciones)\b",
        ),
    ),
    (
        "secrets",
        (
            r"\b(groq_api_key|api[ -]?key|clave (?:de )?api|access token|token de acceso)\b",
            r"\b(revela|muestra|dime|show|reveal|extract)\b.{0,50}\b(secreto|secret|token|credencial)\b",
        ),
    ),
    (
        "prompt_injection",
        (
            r"\b(ignore|disregard|forget|override)\b.{0,50}\b(previous|prior|system|instructions?|rules?)\b",
            r"\b(ignora|olvida|omite|sobrescribe|saltate)\b.{0,50}\b(instrucciones?|reglas?|anteriores?|previas?)\b",
            r"\b(actua|comportate|pretend)\b.{0,20}\b(como|to be)\b",
            r"\b(jailbreak|modo desarrollador|developer mode)\b",
        ),
    ),
    (
        "system_command",
        (
            r"\b(ejecuta|execute|run|lanza)\b.{0,30}\b(comando|command|shell|bash|powershell|cmd)\b",
            r"\brm\s+-rf\b|\bos\.system\b|\bsubprocess\b|\bcmd\.exe\b",
        ),
    ),
    (
        "tool_bypass",
        (
            r"\b(funcion|function|tool|herramienta)\b.{0,35}\b(llamada?|named|borrar|eliminar|delete|inexistente)\b",
            r"\b(salta|evita|bypass|ignora)\b.{0,35}\b(whitelist|lista blanca|validacion|tools?|herramientas?)\b",
            r"\b(cambia|modifica|set)\b.{0,35}\b(directamente|sin (?:usar )?(?:la )?herramienta|without tools?)\b",
        ),
    ),
)


def check_user_input(message: str) -> SecurityResult:
    """Clasifica patrones explícitos de manipulación antes de llamar al modelo."""
    if not isinstance(message, str):
        return SecurityResult(False, "El mensaje no es texto.", "invalid_input")
    normalized = _normalize(message)
    for category, patterns in INPUT_RULES:
        if any(re.search(pattern, normalized, flags=re.DOTALL) for pattern in patterns):
            return SecurityResult(False, "La solicitud está fuera de las operaciones permitidas.", category)
    return SecurityResult(True)


def check_model_output(output: str, system_prompt: str) -> SecurityResult:
    """Bloquea respuestas que parezcan incluir instrucciones internas o secretos."""
    if not isinstance(output, str):
        return SecurityResult(False, "La respuesta no es texto.", "invalid_output")
    normalized = _normalize(output)
    if "groq_api_key" in normalized or "prompt del sistema" in normalized or "system prompt" in normalized:
        return SecurityResult(False, "La respuesta contiene indicadores sensibles.", "sensitive_output")
    if system_prompt and system_prompt in output:
        return SecurityResult(False, "La respuesta replica instrucciones internas.", "internal_instructions")

    for name, value in os.environ.items():
        sensitive_name = any(marker in name.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        if sensitive_name and len(value) >= 8 and value in output:
            return SecurityResult(False, "La respuesta contiene un valor sensible.", "secret_value")
    return SecurityResult(True)
