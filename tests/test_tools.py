import pytest
from app import database
from app.tools import (InventarioError, ProductoNoEncontradoError, StockInsuficienteError,
                       consultar_inventario, listar_productos, registrar_entrada, registrar_venta)


@pytest.fixture(autouse=True)
def base_de_datos_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "inventario_test.db")
    database.initialize_database()


def test_listar_productos():
    productos = listar_productos()
    assert len(productos) == 4
    assert {p["nombre"] for p in productos} == {
        "Camiseta negra", "Camiseta blanca", "Gorra", "Sudadera"
    }


def test_consultar_producto_existente():
    producto = consultar_inventario("  camiseta negra ")
    assert producto["nombre"] == "Camiseta negra"
    assert producto["stock"] == 10


def test_consultar_producto_inexistente():
    with pytest.raises(ProductoNoEncontradoError):
        consultar_inventario("Pantalón")


def test_registrar_entrada_valida():
    assert registrar_entrada("Gorra", 3)["stock"] == 11
    assert consultar_inventario("Gorra")["stock"] == 11


def test_registrar_venta_valida():
    assert registrar_venta("Sudadera", 2)["stock"] == 3
    assert consultar_inventario("Sudadera")["stock"] == 3


def test_no_permite_vender_mas_del_stock_disponible():
    with pytest.raises(StockInsuficienteError):
        registrar_venta("Sudadera", 6)
    assert consultar_inventario("Sudadera")["stock"] == 5


@pytest.mark.parametrize("cantidad", [0, -1])
@pytest.mark.parametrize("operacion", [registrar_entrada, registrar_venta])
def test_rechaza_cantidades_no_positivas(operacion, cantidad):
    with pytest.raises(InventarioError):
        operacion("Gorra", cantidad)
