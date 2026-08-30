"""Cliente HTTP mínimo y sanitizado para la API compatible de OpenRouter."""

from typing import Any

import httpx

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterError(Exception):
    def __init__(self, category: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(category)
        self.category = category
        self.status_code = status_code
        self.code = code


class OpenRouterClient:
    def __init__(self, api_key: str, *, timeout: float = 30.0, http_client: Any = httpx):
        self._api_key = api_key
        self._timeout = timeout
        self._http_client = http_client

    def create(self, *, model: str, messages: list[dict], tools=None, tool_choice=None) -> dict:
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        try:
            response = self._http_client.post(
                OPENROUTER_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as error:
            raise OpenRouterError("timeout") from error
        except httpx.RequestError as error:
            raise OpenRouterError("network") from error

        if not response.is_success:
            code = self._extract_error_code(response)
            category = self._category_for_status(response.status_code)
            raise OpenRouterError(category, status_code=response.status_code, code=code)

        try:
            data = response.json()
            choices = data["choices"]
            message = choices[0]["message"]
            if not isinstance(choices, list) or not choices or not isinstance(message, dict):
                raise TypeError
            content = message.get("content")
            tool_calls = message.get("tool_calls")
            if content is not None and not isinstance(content, str):
                raise TypeError
            if tool_calls is not None and not isinstance(tool_calls, list):
                raise TypeError
            return message
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise OpenRouterError("invalid_response", status_code=response.status_code) from error

    @staticmethod
    def _category_for_status(status_code: int) -> str:
        if status_code in (401, 403):
            return "authentication"
        if status_code == 404:
            return "model_not_found"
        if status_code == 429:
            return "rate_limit"
        if status_code >= 500:
            return "server"
        return "api"

    @staticmethod
    def _extract_error_code(response: Any) -> str | None:
        try:
            body = response.json()
            error = body.get("error", {}) if isinstance(body, dict) else {}
            code = error.get("code") if isinstance(error, dict) else None
            return str(code) if code is not None else None
        except Exception:
            return None
