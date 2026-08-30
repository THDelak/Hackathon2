import os
from pathlib import Path

from app.config import ENV_FILE, PROJECT_ROOT, load_environment


def test_env_file_apunta_a_la_raiz_del_proyecto():
    assert ENV_FILE == PROJECT_ROOT / ".env"
    assert ENV_FILE.parent == Path(__file__).resolve().parent.parent


def test_carga_dotenv_explicito(tmp_path, monkeypatch):
    variable = "TEST_DOTENV_PROJECT_VALUE"
    monkeypatch.delenv(variable, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f"{variable}=valor-de-prueba\n", encoding="utf-8")

    assert load_environment(env_file) is True
    assert os.getenv(variable) == "valor-de-prueba"


def test_variable_del_sistema_tiene_prioridad(tmp_path, monkeypatch):
    variable = "TEST_DOTENV_PRIORITY_VALUE"
    monkeypatch.setenv(variable, "valor-del-sistema")
    env_file = tmp_path / ".env"
    env_file.write_text(f"{variable}=valor-del-archivo\n", encoding="utf-8")

    load_environment(env_file)
    assert os.getenv(variable) == "valor-del-sistema"
