# Hackathon 2: agente de inventario por WhatsApp

Base de un futuro agente de WhatsApp para gestionar inventario y ventas. La etapa
actual incluye SQLite, lógica de negocio, una API local y un agente Llama servido
por Groq con function calling.

## Arquitectura actual

- `app/database.py`: conexión, esquema e inicialización idempotente de SQLite.
- `app/tools.py`: reglas de consulta, entradas y ventas de inventario.
- `app/agent.py`: schemas, whitelist y orquestación de las llamadas a herramientas.
- `app/main.py`: endpoints locales, incluido `POST /agent/chat`.
- `tests/test_tools.py`: pruebas aisladas con una base temporal por prueba.
- `data/`: ubicación predeterminada de la base SQLite local.

WhatsApp Cloud API, Meta, ngrok, Llama Guard, Prompt Guard y las demás capas de
seguridad siguen pendientes para fases posteriores.

## Preparación

Requiere Python 3.10 o posterior. En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

La aplicación usa `data/inventario.db` de forma predeterminada. También puede
definirse `INVENTORY_DATABASE_PATH`, documentada en `.env.example`.

Para usar el agente, define exclusivamente la variable de entorno `GROQ_API_KEY`.
En PowerShell para la sesión actual:

```powershell
$env:GROQ_API_KEY="tu_clave_local"
```

No escribas la clave real en `.env.example` ni la agregues al repositorio.

## Ejecutar la API

```powershell
python -m uvicorn app.main:app --reload
```

La documentación queda disponible en `http://127.0.0.1:8000/docs`.

Prueba el agente localmente desde otra consola:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/agent/chat `
  -ContentType "application/json" `
  -Body '{"message":"¿Cuántas camisetas negras tenemos?"}'
```

El modelo `llama-3.3-70b-versatile` recibe schemas de las cuatro operaciones. Si
solicita una función, la aplicación valida el JSON y el nombre contra una
whitelist, ejecuta la función local de `app/tools.py` y devuelve el resultado al
modelo para redactar la respuesta final. El modelo no modifica SQLite directamente.

## Ejecutar las pruebas

```powershell
python -m pytest
```
