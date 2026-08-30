# Hackathon 2: agente de inventario por WhatsApp

Base local de un futuro agente de WhatsApp para gestionar inventario y ventas. En
esta primera etapa el proyecto contiene únicamente SQLite, lógica de negocio
independiente del LLM y una API local mínima con FastAPI.

## Arquitectura actual

- `app/database.py`: conexión, esquema e inicialización idempotente de SQLite.
- `app/tools.py`: reglas de consulta, entradas y ventas de inventario.
- `app/main.py`: endpoints locales `GET /health` y `GET /productos`.
- `tests/test_tools.py`: pruebas aisladas con una base temporal por prueba.
- `data/`: ubicación predeterminada de la base SQLite local.

WhatsApp Cloud API, Meta, ngrok, Llama, Groq, function calling y la capa de
seguridad se integrarán en fases posteriores.

## Preparación

Requiere Python 3.10 o posterior. En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

La aplicación usa `data/inventario.db` de forma predeterminada. También puede
definirse `INVENTORY_DATABASE_PATH`, documentada en `.env.example`.

## Ejecutar la API

```powershell
python -m uvicorn app.main:app --reload
```

La documentación queda disponible en `http://127.0.0.1:8000/docs`.

## Ejecutar las pruebas

```powershell
python -m pytest
```
