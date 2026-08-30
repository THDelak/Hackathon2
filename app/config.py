"""Carga centralizada de configuración local desde la raíz del proyecto."""

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_environment(dotenv_path: Path = ENV_FILE) -> bool:
    """Carga un archivo dotenv sin reemplazar variables definidas por el sistema."""
    return load_dotenv(dotenv_path=dotenv_path, override=False)
