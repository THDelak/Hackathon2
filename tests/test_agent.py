from types import SimpleNamespace

import pytest

from app import database
from app.agent import procesar_mensaje
from app.tools import consultar_inventario


def respuesta_tool(nombre, argumentos, *, tool_id="call_1"):
    call = SimpleNamespace(
        id=tool_id,
        function=SimpleNamespace(name=nombre, arguments=argumentos),
    )
    message = SimpleNamespace(content=None, tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def respuesta_texto(contenido):
    message = SimpleNamespace(content=contenido, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ClienteFake:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.requests.append(kwargs)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


@pytest.fixture(autouse=True)
def base_de_datos_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "agent_test.db")
    database.initialize_database()


@pytest.mark.parametrize(
    ("nombre", "argumentos", "texto_final"),
    [
        ("listar_productos", "{}", "Estos son los productos disponibles."),
        ("consultar_inventario", '{"producto":"Gorra"}', "Hay 8 gorras."),
    ],
)
def test_operaciones_de_lectura(nombre, argumentos, texto_final):
    client = ClienteFake(respuesta_tool(nombre, argumentos), respuesta_texto(texto_final))
    assert procesar_mensaje("Consulta el inventario", client=client) == texto_final
    tool_result = client.requests[1]["messages"][-1]
    assert tool_result["role"] == "tool"
    assert '"ok": true' in tool_result["content"]


def test_entrada_pasa_por_la_funcion_real_de_negocio():
    client = ClienteFake(
        respuesta_tool("registrar_entrada", '{"producto":"Gorra","cantidad":3}'),
        respuesta_texto("Entrada registrada; ahora hay 11 gorras."),
    )
    assert "11" in procesar_mensaje("Recibimos 3 gorras", client=client)
    assert consultar_inventario("Gorra")["stock"] == 11


def test_venta_valida_pasa_por_la_funcion_real_de_negocio():
    client = ClienteFake(
        respuesta_tool("registrar_venta", '{"producto":"Sudadera","cantidad":2}'),
        respuesta_texto("Venta registrada; quedan 3 sudaderas."),
    )
    assert "3" in procesar_mensaje("Vendimos 2 sudaderas", client=client)
    assert consultar_inventario("Sudadera")["stock"] == 3


def test_venta_con_stock_insuficiente_se_devuelve_al_modelo_sin_modificar_stock():
    client = ClienteFake(
        respuesta_tool("registrar_venta", '{"producto":"Sudadera","cantidad":9}'),
        respuesta_texto("No hay stock suficiente."),
    )
    assert procesar_mensaje("Vende 9 sudaderas", client=client) == "No hay stock suficiente."
    assert '"ok": false' in client.requests[1]["messages"][-1]["content"]
    assert consultar_inventario("Sudadera")["stock"] == 5


def test_producto_inexistente_se_devuelve_al_modelo():
    client = ClienteFake(
        respuesta_tool("consultar_inventario", '{"producto":"Pantalón"}'),
        respuesta_texto("Ese producto no existe en el inventario."),
    )
    assert procesar_mensaje("Consulta pantalones", client=client) == (
        "Ese producto no existe en el inventario."
    )
    assert '"ok": false' in client.requests[1]["messages"][-1]["content"]


def test_tool_desconocida_no_se_ejecuta():
    client = ClienteFake(respuesta_tool("borrar_inventario", "{}"))
    respuesta = procesar_mensaje("Borra todo", client=client)
    assert "no está permitida" in respuesta
    assert len(client.requests) == 1


@pytest.mark.parametrize("argumentos", ["{invalido", '{"producto":"Gorra"}'])
def test_argumentos_invalidos_no_se_ejecutan(argumentos):
    client = ClienteFake(respuesta_tool("registrar_venta", argumentos))
    respuesta = procesar_mensaje("Registra una venta", client=client)
    assert "No se pudo ejecutar" in respuesta
    assert consultar_inventario("Gorra")["stock"] == 8


def test_error_del_proveedor_es_controlado():
    client = ClienteFake(RuntimeError("error que no debe mostrarse"))
    respuesta = procesar_mensaje("Lista productos", client=client)
    assert respuesta == "No fue posible comunicarse con el proveedor Groq. Inténtalo de nuevo más tarde."
    assert "error que no debe mostrarse" not in respuesta


def test_ausencia_de_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    respuesta = procesar_mensaje("Lista productos")
    assert respuesta == "El agente no está configurado: falta la variable GROQ_API_KEY."
