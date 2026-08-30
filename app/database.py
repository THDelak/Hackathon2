"""Configuración y utilidades de acceso a SQLite."""

import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.getenv("INVENTORY_DATABASE_PATH", PROJECT_ROOT / "data" / "inventario.db"))
PRODUCTOS_INICIALES = (("Camiseta negra", 10), ("Camiseta blanca", 10), ("Gorra", 8), ("Sudadera", 5))


def get_connection() -> sqlite3.Connection:
    """Crea una conexión con filas accesibles por nombre de columna."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Crea el esquema y agrega productos iniciales sin duplicarlos."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
                stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
            )
        """)
        connection.executemany(
            "INSERT OR IGNORE INTO productos (nombre, stock) VALUES (?, ?)", PRODUCTOS_INICIALES
        )
