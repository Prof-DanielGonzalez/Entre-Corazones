# Guía técnica

Este documento describe la implementación de Entre Corazones para desarrollo y mantenimiento. Para instalarla en una computadora nueva, consulta el [README principal](README.md). Para explicarla a una persona no técnica, consulta la [guía de presentación](README_PRESENTACION.md).

## Tecnologías

| Área | Tecnología | Función |
| --- | --- | --- |
| Servidor web | Python, Flask | Renderiza la página, valida solicitudes HTTP y expone la API JSON. |
| Producción | Gunicorn | Servidor WSGI; el destino de inicio es `app:app`. |
| Limitación de solicitudes | Flask-Limiter | Aplica límites por dirección IP; la configuración actual guarda contadores en memoria. |
| Interfaz | HTML, Jinja, CSS y JavaScript nativo | Presenta los modos de juego y gestiona formularios, resultados, navegación y almacenamiento local. |
| Persistencia compartida | PostgreSQL y psycopg | Guarda votos comunitarios, feedback y métricas agregadas cuando se configura `DATABASE_URL`. |
| Funciones generativas | OpenAI Python SDK, Responses API | Responde al chat y genera interpretaciones o ideas opcionales solicitadas por el usuario. |
| Imágenes | Pillow | Genera el ícono PWA y la tarjeta Open Graph desde el servidor. |
| Aplicación web progresiva | Web App Manifest y Service Worker | Permite instalar la página y almacenar su interfaz estática para acceso sin conexión. |

No hay framework de frontend ni paso de compilación de JavaScript. Node.js no es necesario para ejecutar la aplicación.

## Arquitectura y responsabilidades

```text
Navegador
  ├── templates/index.html
  ├── static/css/app.css
  ├── static/js/app.js
  └── /api/*
       ↓
app.py → entre_corazones.create_app()
       ├── routes/pages.py
       └── routes/api.py
              ├── services/domain.py
              ├── services/readings.py
              ├── services/ai.py
              └── infrastructure/database.py
```

- **`app.py`** es la fachada WSGI, compatible con `gunicorn app:app` y con `flask --app app`. No concentra las rutas ni la lógica del producto.
- **`entre_corazones/__init__.py`** crea Flask, establece las rutas de plantillas y archivos estáticos, aplica `ProxyFix` cuando existe `RENDER` y registra extensiones, blueprints y el manejador HTTP 429.
- **`entre_corazones/config.py`** define el contenido del juego, los signos, los arcanos, los prompts y los límites de entrada. Carga los datos de `static/common_matches.json` resolviendo su ruta respecto al proyecto.
- **`entre_corazones/extensions.py`** configura Flask-Limiter.
- **`entre_corazones/routes/pages.py`** sirve la página principal, el manifest, el service worker y las imágenes generadas.
- **`entre_corazones/routes/api.py`** contiene los endpoints HTTP y coordina las validaciones, los servicios y las respuestas JSON.
- **`entre_corazones/services/domain.py`** implementa los cálculos deterministas de compatibilidad, las validaciones de fechas y la generación de apodos y sugerencias.
- **`entre_corazones/services/readings.py`** prepara textos y contexto estructurado para los resultados y sus lecturas.
- **`entre_corazones/services/ai.py`** crea el cliente OpenAI, construye respuestas y transmite el chat mediante Server-Sent Events.
- **`entre_corazones/infrastructure/database.py`** abre conexiones PostgreSQL, crea las tablas idempotentemente y registra métricas agregadas.
- **`templates/index.html`** contiene el HTML y las expresiones Jinja.
- **`static/css/app.css`** contiene los estilos; **`static/js/app.js`** controla la navegación de vistas, las interacciones y las solicitudes al servidor.

## Flujo de una solicitud

1. El navegador carga el HTML de Flask y solicita el CSS y JavaScript estáticos.
2. JavaScript cambia las vistas de la aplicación, mantiene la navegación del historial del navegador y envía las acciones del modo elegido a `/api/...`.
3. Flask valida el JSON recibido en `routes/api.py` y llama al servicio correspondiente.
4. Las funciones locales generan el resultado sin proveedor externo; solo las acciones que necesitan IA llaman al servicio OpenAI.
5. Las rutas que dependen de datos compartidos utilizan el módulo PostgreSQL. Si no hay una base configurada, devuelven un error explícito en vez de simular que guardaron los datos.
6. La respuesta JSON se renderiza como resultado en el navegador. El historial privado y las preferencias de la interfaz se conservan en el almacenamiento local del dispositivo.

## Endpoints

| Endpoint | Método | Propósito |
| --- | --- | --- |
| `/` | GET | Interfaz principal. |
| `/manifest.webmanifest` | GET | Configuración instalable de la PWA. |
| `/service-worker.js` | GET | Caché del shell y de los recursos estáticos. Las rutas `/api/` no se cachean. |
| `/app-icon.png`, `/og-card.png` | GET | Imágenes generadas con Pillow. |
| `/api/calcular` | POST | Match de nombres con opciones de signos y fechas. |
| `/api/celebridades` | GET | Opciones de personajes y personas famosas. |
| `/api/match-celebridad`, `/api/ranking`, `/api/match-aleatorio` | POST | Juegos de comparación, ranking y match aleatorio. |
| `/api/test-pareja`, `/api/lectura-completa`, `/api/tarot`, `/api/zodiacal` | POST | Test y lecturas recreativas. |
| `/api/historia-aleatoria`, `/api/idea-ranking`, `/api/ideas-ia`, `/api/profundizar`, `/api/chat` | POST | Opciones de contenido, interpretación y chat que pueden utilizar IA. |
| `/api/feedback` | POST | Agrega feedback sobre una lectura en PostgreSQL. |
| `/api/community`, `/api/community/vote` | GET, POST | Consulta pares de ficción y registra votos comunitarios. |
| `/api/metrics` | GET | Devuelve métricas agregadas tras validar el token administrativo. |

## Cálculos, IA y persistencia

- El match de nombres utiliza un cálculo determinista y una caché LRU limitada a 2048 entradas. Los pares precargados de `static/common_matches.json` pueden reemplazar ciertos resultados.
- Los cálculos de fechas, compatibilidad de signos, tarot y test no requieren IA. Son lecturas de entretenimiento y no representan evaluaciones científicas.
- `OPENAI_API_KEY` habilita las funciones generativas. `OPENAI_MODEL` permite sobrescribir el modelo configurado por defecto en el código. Las llamadas usan Responses API y solicitan `store=False`; el texto se envía al proveedor para generar la respuesta y la aplicación no conserva una copia del intercambio en su base PostgreSQL.
- El chat puede transmitir deltas de texto como eventos `text/event-stream`.
- `DATABASE_URL` habilita PostgreSQL. Al primer uso, `infrastructure/database.py` crea las tablas `daily_metrics`, `daily_feedback` y `community_votes`.
- El dashboard contrasta el encabezado `X-Metrics-Token` con `METRICS_ADMIN_TOKEN`. La votación utiliza `COMMUNITY_VOTE_SALT` y un hash del identificador aleatorio del navegador.
- La interfaz guarda historial, chat y cápsulas en `localStorage`; esos datos pertenecen al navegador en que se guardaron.

## Límites y operación

- Flask-Limiter utiliza almacenamiento en memoria. Sus contadores no se comparten entre procesos o instancias y se reinician al reiniciar el servidor; no reemplazan los límites de gasto del proveedor de IA.
- Si se requieren límites compartidos al escalar, configura en Flask-Limiter un almacenamiento persistente compatible, por ejemplo Redis.
- Sin `OPENAI_API_KEY`, las opciones de IA informan que el servicio no está configurado; los modos que no necesitan IA continúan disponibles.
- Sin `DATABASE_URL`, la interfaz sigue ejecutándose, pero las funciones de comunidad, feedback y dashboard necesitan la base de datos.
- El Service Worker almacena la interfaz estática; las acciones de IA, votaciones y métricas necesitan conexión.
- En Render el punto de entrada sigue siendo `gunicorn app:app`. `ProxyFix` se activa cuando el entorno establece `RENDER`.

## Desarrollo y verificación

Desde la raíz del repositorio, crea y activa un entorno virtual, instala `requirements.txt` y ejecuta:

```bash
python -m flask --app app run --debug
```

Verificaciones disponibles con Python y Node.js instalados:

```bash
python -m compileall -q app.py entre_corazones
node --check static/js/app.js
git diff --check
```

El repositorio no incluye actualmente una suite automatizada de pruebas. Al modificar una ruta, conviene verificar su método, validación, código HTTP y forma JSON, además de comprobar que `/`, el manifest, el Service Worker y los recursos estáticos carguen.
