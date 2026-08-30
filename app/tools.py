"""Funciones de negocio para consultar y modificar el inventario."""

from app.database import get_connection, initialize_database


class InventarioError(ValueError):
    """Error controlado de las operaciones de inventario."""


class ProductoNoEncontradoError(InventarioError):
    """El producto solicitado no existe."""


class StockInsuficienteError(InventarioError):
    """No hay suficiente stock para completar una venta."""


def _validar_cantidad(cantidad: int) -> None:
    if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
        raise InventarioError("La cantidad debe ser un número entero mayor que cero.")


def _validar_producto(producto: str) -> str:
    if not isinstance(producto, str) or not producto.strip():
        raise InventarioError("El nombre del producto no puede estar vacío.")
    return producto.strip()


def listar_productos() -> list[dict]:
    initialize_database()
    with get_connection() as connection:
        rows = connection.execute("SELECT id, nombre, stock FROM productos ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def consultar_inventario(producto: str) -> dict:
    nombre = _validar_producto(producto)
    initialize_database()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, nombre, stock FROM productos WHERE nombre = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    if row is None:
        raise ProductoNoEncontradoError(f"No existe el producto: {nombre}.")
    return dict(row)


def registrar_entrada(producto: str, cantidad: int) -> dict:
    nombre = _validar_producto(producto)
    _validar_cantidad(cantidad)
    initialize_database()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE productos SET stock = stock + ? WHERE nombre = ? COLLATE NOCASE", (cantidad, nombre)
        )
        if cursor.rowcount == 0:
            raise ProductoNoEncontradoError(f"No existe el producto: {nombre}.")
        row = connection.execute(
            "SELECT id, nombre, stock FROM productos WHERE nombre = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    return dict(row)


def registrar_venta(producto: str, cantidad: int) -> dict:
    nombre = _validar_producto(producto)
    _validar_cantidad(cantidad)
    initialize_database()
    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE productos SET stock = stock - ?
            WHERE nombre = ? COLLATE NOCASE AND stock >= ?
        """, (cantidad, nombre, cantidad))
        if cursor.rowcount == 0:
            actual = connection.execute(
                "SELECT stock FROM productos WHERE nombre = ? COLLATE NOCASE", (nombre,)
            ).fetchone()
            if actual is None:
                raise ProductoNoEncontradoError(f"No existe el producto: {nombre}.")
            raise StockInsuficienteError(
                f"Stock insuficiente para {nombre}: disponible {actual['stock']}."
            )
        row = connection.execute(
            "SELECT id, nombre, stock FROM productos WHERE nombre = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    return dict(row)
