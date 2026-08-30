from types import SimpleNamespace

import httpx
import pytest

from app.openrouter import OPENROUTER_CHAT_URL, OpenRouterClient, OpenRouterError


class FakeResponse:
    def __init__(self, status_code=200, body=None, json_error=None):
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self.body = body
        self.json_error = json_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.body


class FakeHttp:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_request_openrouter_incluye_modelo_tools_y_timeout():
    http = FakeHttp(FakeResponse(body={"choices": [{"message": {"content": "OK"}}]}))
    client = OpenRouterClient("key-de-prueba", timeout=30.0, http_client=http)
    result = client.create(
        model="meta-llama/llama-4-maverick",
        messages=[{"role": "user", "content": "Hola"}],
        tools=[{"type": "function", "function": {"name": "demo"}}],
        tool_choice="auto",
    )
    assert result == {"content": "OK"}
    url, request = http.calls[0]
    assert url == OPENROUTER_CHAT_URL
    assert request["timeout"] == 30.0
    assert request["headers"]["Authorization"] == "Bearer key-de-prueba"
    assert request["json"]["model"] == "meta-llama/llama-4-maverick"
    assert request["json"]["tool_choice"] == "auto"


@pytest.mark.parametrize(
    ("status", "category"),
    [(401, "authentication"), (403, "authentication"), (404, "model_not_found"),
     (429, "rate_limit"), (500, "server"), (503, "server")],
)
def test_errores_http_se_clasifican_sin_body(status, category):
    response = FakeResponse(status, {"error": {"code": "codigo-sanitizado", "message": "secreto"}})
    client = OpenRouterClient("key-de-prueba", http_client=FakeHttp(response))
    with pytest.raises(OpenRouterError) as captured:
        client.create(model="modelo", messages=[])
    assert captured.value.category == category
    assert captured.value.status_code == status
    assert captured.value.code == "codigo-sanitizado"
    assert "secreto" not in str(captured.value)


def test_timeout_se_clasifica():
    request = httpx.Request("POST", OPENROUTER_CHAT_URL)
    http = FakeHttp(error=httpx.ReadTimeout("detalle sensible", request=request))
    client = OpenRouterClient("key-de-prueba", http_client=http)
    with pytest.raises(OpenRouterError) as captured:
        client.create(model="modelo", messages=[])
    assert captured.value.category == "timeout"
    assert "detalle sensible" not in str(captured.value)


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(body={}),
        FakeResponse(body={"choices": []}),
        FakeResponse(body={"choices": [{"message": "inválido"}]}),
        FakeResponse(json_error=ValueError("json inválido")),
    ],
)
def test_respuesta_invalida_se_rechaza(response):
    client = OpenRouterClient("key-de-prueba", http_client=FakeHttp(response))
    with pytest.raises(OpenRouterError) as captured:
        client.create(model="modelo", messages=[])
    assert captured.value.category == "invalid_response"
