# Entre Corazones

Entre Corazones es una aplicación web adaptable a móviles y computadoras para jugar con temas de vínculos y relaciones. Incluye compatibilidad de nombres, tests, tarot y astrología simbólicos, juegos con personajes, una sección comunitaria y una conversación opcional con IA.

Los porcentajes, las cartas y las lecturas son recreativos: no son medidas científicas, predicciones ni asesoramiento profesional.

## Documentación

- [Guía técnica: tecnologías, arquitectura y funcionamiento](README_TECNICO.md)
- [Guía para presentar el proyecto](README_PRESENTACION.md)
- Esta página explica cómo instalarlo y ejecutarlo en otra computadora.

## Requisitos

- Git.
- Python 3.10 o posterior.
- Acceso a internet para instalar las dependencias. La aplicación local no necesita Node.js.

## Instalar en Windows

Abre PowerShell y ejecuta:

```powershell
git clone https://github.com/Prof-DanielGonzalez/Entre-Corazones.git
cd Entre-Corazones
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flask --app app run --debug
```

Abre <http://127.0.0.1:5000/> en el navegador. Para detener el servidor, vuelve a PowerShell y pulsa `Ctrl+C`.

Si PowerShell impide activar el entorno virtual, permite la activación solo para la terminal actual y vuelve a intentarlo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Instalar en macOS o Linux

En una terminal, ejecuta:

```bash
git clone https://github.com/Prof-DanielGonzalez/Entre-Corazones.git
cd Entre-Corazones
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flask --app app run --debug
```

Abre <http://127.0.0.1:5000/> en el navegador. Para detener el servidor, pulsa `Ctrl+C`.

## Funciones opcionales y configuración

Los juegos y lecturas locales funcionan sin claves externas. Si quieres habilitar las funciones de IA, configura `OPENAI_API_KEY` antes de iniciar el servidor.

En PowerShell:

```powershell
$env:OPENAI_API_KEY = "tu-clave-de-OpenAI"
python -m flask --app app run --debug
```

En macOS o Linux:

```bash
export OPENAI_API_KEY="tu-clave-de-OpenAI"
python -m flask --app app run --debug
```

Variables disponibles:

| Variable | ¿Es necesaria? | Uso |
| --- | --- | --- |
| `OPENAI_API_KEY` | No | Habilita el chat y las opciones de interpretación con IA. |
| `OPENAI_MODEL` | No | Sobrescribe el modelo usado por OpenAI. Si no se configura, se utiliza el valor predeterminado de la aplicación. |
| `DATABASE_URL` | No para el uso local básico | Conexión PostgreSQL para votos comunitarios, feedback y métricas. Sin ella, las páginas y los juegos locales siguen disponibles, pero las funciones que guardan o leen datos compartidos no funcionan. |
| `METRICS_ADMIN_TOKEN` | No | Protege el endpoint del dashboard agregado de métricas. |
| `COMMUNITY_VOTE_SALT` | No | Secreto del servidor para generar identificadores hash al limitar votos repetidos. |

Las variables para servicios desplegados se configuran en el entorno del servidor, por ejemplo, en Render; no se escriben en el código ni se suben a GitHub. Si se generan secretos para `METRICS_ADMIN_TOKEN` y `COMMUNITY_VOTE_SALT`, usa valores largos y distintos. El archivo `.env` está ignorado por Git, pero la instalación base no carga ese archivo automáticamente.

## Ejecutar para producción

Con las dependencias instaladas, Gunicorn puede iniciar la aplicación mediante el punto de entrada compatible:

```bash
gunicorn app:app
```

En Render, configura:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`

Configura allí las variables de entorno que requieran las funciones habilitadas. Para PostgreSQL, crea una base persistente y utiliza su `DATABASE_URL`. Las tablas necesarias se preparan automáticamente cuando se usa la base.

## Estructura del proyecto

```text
.
├── app.py
├── entre_corazones/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── infrastructure/
│   ├── routes/
│   └── services/
├── static/
│   ├── common_matches.json
│   ├── css/app.css
│   └── js/app.js
├── templates/index.html
└── requirements.txt
```

Consulta la [guía técnica](README_TECNICO.md) para conocer las responsabilidades de cada capa y el flujo de una solicitud.

## Privacidad y costos

- El cálculo de nombres y varias lecturas se realizan localmente.
- Las funciones de IA envían a OpenAI el texto necesario para atender la acción elegida. Se solicita `store=False`, pero eso no significa que el texto nunca salga del servicio de la aplicación.
- El historial de chat, lecturas y cápsulas se guarda en el almacenamiento local de ese navegador; no es una sincronización entre dispositivos.
- PostgreSQL se utiliza para los datos agregados y las votaciones descritas en la [guía técnica](README_TECNICO.md), no para crear perfiles de usuario.
- OpenAI puede cobrar por el uso de su API. Revisa sus precios y política de privacidad antes de habilitar la clave.

No publiques claves ni secretos en el repositorio, capturas, registros compartidos o conversaciones públicas.
