# Entre Corazones

Aplicación Flask con juegos de compatibilidad, lecturas simbólicas y una conversación opcional con OpenAI.

## Ejecutar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY = "tu-clave-secreta"
flask --app app run
```

No compartas ni subas la clave. Para que las lecturas y el resto de la página funcionen sin IA, puedes iniciar Flask sin configurar `OPENAI_API_KEY`.

## Desplegar en Render

Conecta este repositorio como **Web Service** con:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

En **Environment**, añade `OPENAI_API_KEY` con una clave de API de OpenAI. Opcionalmente, configura `OPENAI_MODEL` (por defecto `gpt-4o-mini`). Nunca incluyas la clave en GitHub ni en el HTML.

Las funciones con IA responden con un aviso si la clave no está configurada. El proveedor puede cobrar por las solicitudes; configura límites de uso en tu proyecto de OpenAI y revisa su política de privacidad antes de compartir la aplicación.

## Privacidad del chat

El historial del chat se guarda en `localStorage` del navegador de la persona y puede borrarse desde la interfaz. Para generar cada respuesta, los mensajes recientes de la conversación se envían al servidor y a OpenAI. No se guardan en una base de datos de esta aplicación. Las lecturas de tarot, astrología y compatibilidad son recreativas, no predicciones ni asesoramiento profesional.
