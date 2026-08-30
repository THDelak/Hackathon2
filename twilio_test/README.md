# Adaptador temporal: Twilio WhatsApp Sandbox

Este código existe únicamente para pruebas end-to-end mientras se completa el
registro de Meta. La integración oficial sigue siendo WhatsApp Cloud API y toda la
carpeta `twilio_test/` debe eliminarse antes de la entrega.

No agregues Account SID, Auth Token, API keys ni otros secretos a esta carpeta o al
repositorio. Este endpoint temporal no valida `X-Twilio-Signature`, por lo que solo
debe exponerse durante una prueba controlada mediante ngrok.

## Ejecutar

```powershell
python -m uvicorn twilio_test.app:app --host 0.0.0.0 --port 8000
```

En otra consola:

```powershell
ngrok http 8000
```

En Twilio Console, dentro de WhatsApp Sandbox, configura **WHEN A MESSAGE COMES IN**:

```text
https://<ngrok-domain>/twilio/webhook
```

Selecciona el método `POST`. No guardes en el repositorio el dominio temporal real.

## Comportamiento

El adaptador interpreta `application/x-www-form-urlencoded`, usa `From` como
`conversation_id`, pasa `Body` sin duplicar ninguna lógica a `procesar_mensaje()` y
devuelve su respuesta como XML TwiML escapado.

La idempotencia conserva hasta 1,000 `MessageSid` recientes en memoria. Cada SID se
reserva antes de llamar al agente y los duplicados reciben HTTP 200 con TwiML vacío.
La semántica es **at most once**: ante una excepción inesperada se devuelve un error
seguro y el SID queda completado para priorizar que una venta nunca se repita.

El registro se pierde al reiniciar el proceso y no se comparte entre workers. No
hay validación de firma Twilio, persistencia, cola ni reintentos. Estas limitaciones
son aceptables solo para la prueba temporal y no para producción.
