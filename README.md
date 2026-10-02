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

En **Environment**, configura:

- `OPENAI_API_KEY`: clave privada de OpenAI. La aplicación usa Responses API y por defecto el modelo `gpt-6-luna`; puedes sobrescribirlo con `OPENAI_MODEL`. Nunca incluyas la clave en GitHub ni en el HTML.
- `DATABASE_URL`: URL de una base de datos PostgreSQL persistente. En Render, crea una **PostgreSQL** y enlaza su URL interna como variable del Web Service. Los votos comunitarios y el dashboard dependen de esta base; sin ella, los juegos locales siguen funcionando y esas rutas devuelven un error explícito.
- `METRICS_ADMIN_TOKEN`: secreto aleatorio largo, solo en el servidor. Se solicita en el dashboard interno y no se guarda en el navegador.
- `COMMUNITY_VOTE_SALT`: secreto aleatorio largo para generar hashes no reversibles de identificadores aleatorios de voto. Mantén el mismo valor entre despliegues y no lo publiques.

Las tablas de métricas, feedback y votos se crean automáticamente al usar esas funciones. Usa una base de datos persistente en producción; no se requiere guardar perfiles ni conversaciones.

Las funciones con IA responden con un aviso si la clave no está configurada. Las solicitudes se hacen con `store=False`; aun así, se envían al proveedor para que genere la respuesta. El proveedor puede cobrar por las solicitudes; configura límites de uso en tu proyecto de OpenAI y revisa su política de privacidad antes de compartir la aplicación.

## Estilos y límites de uso

El match de nombres, el chat y las interpretaciones con IA permiten elegir entre los estilos natural, romántico/poético, cómico con sarcasmo suave, místico/astrológico y directo con picardía no explícita. El match admite fechas o signos opcionales. Incluye comparaciones con personajes y famosos, un ranking recreativo de 3 o 4 nombres con comentario IA opcional, un resultado aleatorio con microhistoria IA opcional, apodos, dos green flags, dos puntos para conversar y tres ideas de cita. El archivo `static/common_matches.json` contiene algunas respuestas locales pre-renderizadas; el resto de los matches también se calcula localmente y no consume tokens. El test de pareja compara cuatro respuestas como una actividad para conversar, no como una evaluación psicológica.

El chat se limita inicialmente a 8 mensajes por minuto y 40 al día por IP; profundizar, pedir extras de IA e inventar una historia con IA se limita a 5 por minuto y 20 al día. Los endpoints recreativos tienen límites básicos para reducir abuso. El limitador usa almacenamiento en memoria: los contadores se reinician al reiniciar el proceso y no se comparten entre procesos o instancias. No es un límite global de facturación. Si se escala, configura un almacenamiento compartido compatible, como Redis, y límites de gasto en OpenAI.

El chat de IA transmite el texto con Server-Sent Events para mostrarlo a medida que llega. Los resultados incluyen texto para compartir, PNG horizontal y sticker cuadrado generados en el navegador, WhatsApp, cápsulas temporales con recordatorio `.ics`, historial local y enlaces de desafío. El modo comunitario ofrece pares de ficción preseleccionados. No solicita nombres: PostgreSQL guarda solo el voto, su fecha y un hash con sal de un identificador aleatorio para limitar votos repetidos por navegador; no guarda direcciones IP. El dashboard requiere `METRICS_ADMIN_TOKEN` y muestra totales agregados de los últimos 30 días, sin nombres ni mensajes.

Hay temas rosa/noche/neón, sonido suave opt-in, vibración breve, partículas para resultados altos, controles de texto grande/alto contraste/lectura en voz alta y un efecto de movimiento que solo solicita el sensor después de que el usuario lo activa. La PWA almacena la interfaz para abrirla offline; las solicitudes de IA, votaciones y métricas requieren conexión. El recordatorio de cápsula se muestra al volver a abrir la página; el archivo `.ics` permite añadir un aviso al calendario del dispositivo.

Los resultados de compatibilidad y el cálculo de nombres son deterministas y no llaman a OpenAI; por eso no hay una caché de respuestas de IA para esos modos. El cálculo del match usa una caché LRU pequeña solo para evitar repetir el cálculo local. No se cachean preguntas ni respuestas privadas del chat.

## Privacidad del chat

El historial del chat, las lecturas y las cápsulas se guardan en `localStorage` y pueden borrarse con **Limpiar todo**. Las cápsulas incluyen el resultado que eliges guardar y permanecen en ese navegador. La historia aleatoria base y las compatibilidades se generan localmente; solo al pulsar una acción de IA se envía el contexto mostrado (y, según el modo, los nombres) a OpenAI con `store=False`. El voto comunitario es voluntario; los resultados no permiten identificar a una persona. Los nombres recibidos en enlaces de desafío se quitan de la barra del navegador después de precargar el formulario, aunque la solicitud inicial puede quedar en los logs del alojamiento. Evita datos sensibles. Las lecturas de tarot, astrología y compatibilidad son recreativas, no predicciones ni asesoramiento profesional.
