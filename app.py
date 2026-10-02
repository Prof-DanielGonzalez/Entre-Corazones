import hashlib
import hmac
from functools import lru_cache
from io import BytesIO
import json
import os
import random
import re
import unicodedata
import threading
from datetime import date

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from openai import OpenAI, OpenAIError
from PIL import Image, ImageDraw, ImageFont
import psycopg
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
if os.getenv("RENDER"):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    strategy="fixed-window",
    headers_enabled=True,
)
DATABASE_SCHEMA_READY = False
DATABASE_SCHEMA_LOCK = threading.Lock()
METRICS_WARNING_LOGGED = False

CELEBRITIES = (
    ("Wednesday Addams", "Personaje"),
    ("Shrek", "Personaje"),
    ("Barbie", "Personaje"),
    ("Spider-Man", "Personaje"),
    ("Elizabeth Bennet", "Personaje"),
    ("Luna Lovegood", "Personaje"),
    ("Pedro Pascal", "Famoso"),
    ("Zendaya", "Famosa"),
)
COMMUNITY_PAIRS = {
    "shrek-fiona": ("Shrek + Fiona", "Una pareja de cuento, con pantano y todo."),
    "barbie-ken": ("Barbie + Ken", "Moda, playa y conversaciones pendientes."),
    "morticia-gomez": ("Morticia + Gomez", "Romance intenso y baile en la sala."),
    "luna-neville": ("Luna + Neville", "Rareza adorable y valentía tranquila."),
}


def clave_par_normalizada(nombre1, nombre2):
    partes = (
        unicodedata.normalize("NFKD", nombre1).encode("ascii", "ignore").decode("ascii").casefold().strip(),
        unicodedata.normalize("NFKD", nombre2).encode("ascii", "ignore").decode("ascii").casefold().strip(),
    )
    return "|".join(sorted(partes))


with open(os.path.join(os.path.dirname(__file__), "static", "common_matches.json"), encoding="utf-8") as archivo:
    COMMON_MATCHES = {
        clave_par_normalizada(item["names"][0], item["names"][1]): item
        for item in json.load(archivo)
    }

MAX_CHAT_MESSAGES = 12
MAX_CHAT_MESSAGE_LENGTH = 1500
MAX_READING_QUESTION_LENGTH = 500
VIBE_PROMPTS = {
    "natural": "Usa un tono natural, cálido y equilibrado.",
    "romantico": "Usa un tono romántico y poético, delicado y esperanzador, sin exagerar ni prometer destinos.",
    "comico": "Usa un tono cómico, juguetón y con sarcasmo suave, nunca cruel ni burlón con quien consulta.",
    "mistico": "Usa un tono místico y astrológico como recurso simbólico, dejando claro que no describe hechos ni predice el futuro.",
    "directo": "Usa un tono directo, franco y respetuoso, con picardía ligera pero sin contenido sexual explícito ni presionar límites.",
}
LOVE_CHAT_PROMPT = (
    "Eres Entre Corazones, un acompañante conversacional empático y cercano que responde en español "
    "sobre vínculos, citas, rupturas, autoestima y comunicación. Escucha sin juzgar, refleja lo que la "
    "persona cuenta y ofrece ideas concretas como posibilidades, no órdenes. No afirmes saber lo que "
    "otra persona siente, no predigas el futuro ni presentes compatibilidad, tarot o astrología como "
    "hechos. No diagnostiques ni sustituyas terapia. Evita fomentar dependencia o insistir en una "
    "relación dañina; respeta límites y consentimiento. Si la persona describe peligro inmediato o "
    "violencia, prioriza su seguridad y anímala a contactar servicios de emergencia o alguien de "
    "confianza en su zona. No pidas datos personales innecesarios. Mantén las respuestas cálidas, "
    "específicas y breves, e invita a profundizar con una pregunta cuando ayude."
)

READING_PROMPTS = {
    "names": "match de nombres",
    "complete": "lectura completa de afinidad",
    "tarot": "tirada simbólica de tarot del amor",
    "zodiac": "lectura simbólica de compatibilidad zodiacal",
    "quiz": "test lúdico de preguntas para parejas",
    "celebrity": "match lúdico con personajes o personas famosas",
    "ranking": "ranking recreativo de compatibilidad",
    "random": "match aleatorio e imaginario",
}


SIGNOS = [
    ("Acuario", (1, 20), "aire", "original e independiente"),
    ("Piscis", (2, 19), "agua", "sensible e imaginativo"),
    ("Aries", (3, 21), "fuego", "valiente y espontáneo"),
    ("Tauro", (4, 20), "tierra", "leal y paciente"),
    ("Géminis", (5, 21), "aire", "curioso y comunicativo"),
    ("Cáncer", (6, 21), "agua", "cariñoso y protector"),
    ("Leo", (7, 23), "fuego", "cálido y expresivo"),
    ("Virgo", (8, 23), "tierra", "observador y detallista"),
    ("Libra", (9, 23), "aire", "diplomático y sociable"),
    ("Escorpio", (10, 23), "agua", "intenso y perspicaz"),
    ("Sagitario", (11, 22), "fuego", "optimista y aventurero"),
    ("Capricornio", (12, 22), "tierra", "constante y práctico"),
]

ARCANOS = [
    ("El Sol", "☀️", "claridad, alegría y confianza", "Deja que la alegría compartida ocupe un lugar central; la honestidad puede acercarlos."),
    ("La Estrella", "⭐", "esperanza, calma y autenticidad", "Hay espacio para recuperar la ilusión. Muéstrate tal como eres, sin intentar acelerar el vínculo."),
    ("La Emperatriz", "🌸", "cuidado, ternura y crecimiento", "Nutre el vínculo con pequeños gestos y atención genuina; lo que se cuida puede florecer."),
    ("Los Enamorados", "💞", "elecciones, afinidad y honestidad", "La conexión se fortalece cuando ambos pueden elegir con libertad y hablar con claridad."),
    ("La Templanza", "🕊️", "equilibrio, paciencia y diálogo", "Busca el punto medio y dale tiempo a la conversación. Escuchar también es una forma de acercarse."),
    ("La Luna", "🌙", "intuición, emociones y preguntas", "Puede haber sentimientos que aún no encuentran palabras. No llenes los silencios con suposiciones; pregunta con cariño."),
    ("La Fuerza", "🦁", "confianza, valentía y paciencia", "La fortaleza de esta conexión está en la ternura, no en forzar nada. Avanza con seguridad y respeto."),
    ("El Mundo", "🌍", "plenitud, apertura y nuevos ciclos", "Una etapa puede estar cerrándose para dar paso a otra. Celebra lo aprendido y mantén la mente abierta."),
    ("El Mago", "✨", "iniciativa, comunicación y posibilidades", "Tienes más herramientas de las que crees para crear un momento especial. Un gesto sencillo puede iniciar algo bonito."),
    ("La Sacerdotisa", "🔮", "intuición, reflexión y escucha", "Tómate un momento para reconocer lo que sientes. La calma te ayudará a distinguir intuición de expectativa."),
    ("El Carro", "🏇", "dirección, decisión y movimiento", "Si sabes lo que quieres, exprésalo con amabilidad. El avance más sano ocurre cuando las dos personas marcan el ritmo."),
    ("La Rueda de la Fortuna", "🎡", "cambios, oportunidades y sorpresa", "Algo puede cambiar cuando menos lo esperas. Mantén la curiosidad y recibe las novedades sin aferrarte a un resultado."),
    ("El Ermitaño", "🏮", "espacio, reflexión y autoconocimiento", "Un poco de espacio puede dar perspectiva. Cuida también tu mundo propio mientras descubres qué deseas compartir."),
    ("La Justicia", "⚖️", "reciprocidad, claridad y acuerdos", "Busca una relación donde los gestos y las palabras sean recíprocos. Hablar de expectativas evita malentendidos."),
    ("El Loco", "🦋", "espontaneidad, apertura y comienzos", "Permítete disfrutar de lo nuevo sin exigir certezas inmediatas. La curiosidad puede ser un buen primer paso."),
    ("El Colgado", "🪷", "pausa, perspectiva y paciencia", "Mirar la situación desde otro ángulo puede cambiarlo todo. No confundas una pausa con una respuesta definitiva."),
    ("La Muerte", "🍂", "transformación, cierre y renovación", "Una forma antigua de relacionarse puede estar cambiando. Soltar expectativas rígidas deja sitio a un comienzo más honesto."),
    ("El Juicio", "🕊️", "conversaciones, renovación y comprensión", "Una conversación sincera puede ayudar a entender lo que ambos necesitan. Escucha sin juzgarte ni juzgar a la otra persona."),
    ("El Diablo", "🔥", "deseo, límites y honestidad", "La atracción puede ser intensa; acompáñala con límites claros y decisiones que te hagan sentir bien contigo."),
    ("La Torre", "⚡", "verdad, cambios y liberación", "Si algo se siente inestable, la honestidad es más útil que fingir que todo está bien. Los cambios también pueden abrir caminos."),
    ("El Emperador", "👑", "estabilidad, compromiso y estructura", "La seguridad se construye con acciones consistentes. Expresa qué necesitas y pregunta qué le da tranquilidad a la otra persona."),
    ("El Hierofante", "📜", "valores, confianza y acuerdos", "Compartir valores puede dar una base sólida. Conversen sobre lo importante sin asumir que desean exactamente lo mismo."),
]


@lru_cache(maxsize=2048)
def calculadora_de_amor(nombre1, nombre2):
    # Combinar los nombres y generar un hash MD5
    nombres_combinados = nombre1.lower() + nombre2.lower()
    hash_object = hashlib.md5(nombres_combinados.encode())
    hash_hex = hash_object.hexdigest()

    # Convertir el hash a un número entre 0 y 100
    puntaje_de_amor = int(hash_hex, 16) % 101
    return puntaje_de_amor


def obtener_signo(fecha_nacimiento):
    mes, dia = fecha_nacimiento.month, fecha_nacimiento.day
    signo_actual = SIGNOS[-1][0]
    for nombre, (mes_inicio, dia_inicio), _, _ in SIGNOS:
        if (mes, dia) >= (mes_inicio, dia_inicio):
            signo_actual = nombre
        else:
            break
    return signo_actual


def compatibilidad_signos(signo1, signo2):
    elementos = {nombre: elemento for nombre, _, elemento, _ in SIGNOS}
    elemento1, elemento2 = elementos[signo1], elementos[signo2]
    if elemento1 == elemento2:
        return 88, "Hay una comprensión natural entre sus ritmos y maneras de expresarse."
    relaciones = {
        frozenset(("fuego", "aire")): (84, "La curiosidad y la energía pueden alimentar una conexión muy dinámica."),
        frozenset(("tierra", "agua")): (82, "La estabilidad y la sensibilidad pueden ofrecerse un apoyo valioso."),
        frozenset(("fuego", "agua")): (63, "La intensidad se vive de maneras distintas; escuchar y respetar los ritmos será clave."),
        frozenset(("aire", "tierra")): (67, "Las ideas y lo práctico pueden complementarse si encuentran un ritmo compartido."),
        frozenset(("fuego", "tierra")): (70, "La iniciativa y la constancia se equilibran cuando dejan espacio a las diferencias."),
        frozenset(("aire", "agua")): (68, "La conversación y la sensibilidad pueden encontrarse si expresan con claridad lo que necesitan."),
    }
    return relaciones[frozenset((elemento1, elemento2))]


def validar_fecha(valor, campo):
    try:
        fecha = date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Indica una fecha de nacimiento válida para {campo}.")
    if fecha > date.today():
        raise ValueError(f"La fecha de nacimiento de {campo} no puede estar en el futuro.")
    return fecha


def obtener_datos_json():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


def conectar_base_datos():
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("Configura DATABASE_URL con una conexión PostgreSQL persistente.")
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    conexion = psycopg.connect(dsn, connect_timeout=4)
    global DATABASE_SCHEMA_READY
    if not DATABASE_SCHEMA_READY:
        try:
            with DATABASE_SCHEMA_LOCK:
                if not DATABASE_SCHEMA_READY:
                    with conexion.cursor() as cursor:
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS daily_metrics (
                                metric_date date PRIMARY KEY,
                                matches bigint NOT NULL DEFAULT 0,
                                score_total bigint NOT NULL DEFAULT 0,
                                readings bigint NOT NULL DEFAULT 0
                            )
                        """)
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS daily_feedback (
                                metric_date date NOT NULL,
                                mode text NOT NULL,
                                rating smallint NOT NULL CHECK (rating IN (-1, 1)),
                                total bigint NOT NULL DEFAULT 0,
                                PRIMARY KEY (metric_date, mode, rating)
                            )
                        """)
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS community_votes (
                                pair_id text NOT NULL,
                                voter_hash char(64) NOT NULL,
                                vote boolean NOT NULL,
                                created_at timestamptz NOT NULL DEFAULT now(),
                                PRIMARY KEY (pair_id, voter_hash)
                            )
                        """)
                    conexion.commit()
                    DATABASE_SCHEMA_READY = True
        except psycopg.Error:
            conexion.close()
            raise
    return conexion


def registrar_metrica(match=False, score=None):
    global METRICS_WARNING_LOGGED
    if not os.getenv("DATABASE_URL"):
        if not METRICS_WARNING_LOGGED:
            app.logger.warning("Las métricas anónimas están desactivadas: falta DATABASE_URL.")
            METRICS_WARNING_LOGGED = True
        return
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_metrics (metric_date, matches, score_total, readings)
                VALUES (CURRENT_DATE, %s, %s, %s)
                ON CONFLICT (metric_date) DO UPDATE SET
                    matches = daily_metrics.matches + EXCLUDED.matches,
                    score_total = daily_metrics.score_total + EXCLUDED.score_total,
                    readings = daily_metrics.readings + EXCLUDED.readings
                """,
                (1 if match else 0, int(score or 0) if match else 0, 0 if match else 1),
            )
    except (psycopg.Error, RuntimeError):
        app.logger.exception("No se pudo registrar una métrica agregada y anónima.")


def respuesta_base_datos_no_disponible(error):
    app.logger.exception("No se pudo completar la operación de PostgreSQL.", exc_info=error)
    return jsonify({"error": "La función compartida no está disponible. Revisa la conexión PostgreSQL del servidor e inténtalo más tarde."}), 503


def calcular_apodos(nombre1, nombre2):
    primera = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", nombre1)
    segunda = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", "", nombre2)
    primera = primera or "Cupido"
    segunda = segunda or "Corazón"
    mitad1 = max(1, (len(primera) + 1) // 2)
    mitad2 = max(1, len(segunda) // 2)
    posibles = (
        (primera[:mitad1] + segunda[mitad2:]).capitalize(),
        (segunda[:mitad2] + primera[mitad1:]).capitalize(),
        (primera[:max(1, len(primera) // 3)] + segunda[-max(1, len(segunda) // 3):]).capitalize(),
        (segunda[:max(1, len(segunda) // 3)] + primera[-max(1, len(primera) // 3):]).capitalize(),
        f"{primera} + {segunda}",
        f"{segunda} × {primera}",
        f"{primera} & {segunda}",
    )
    apodos = list(dict.fromkeys(posibles))
    return apodos[:4]


def extras_de_match(puntaje):
    if puntaje >= 70:
        verdes = ["Hay curiosidad y ganas de conocerse.", "La conexión puede crecer con comunicación honesta."]
        rojas = ["No conviertan la química en presión por definirlo todo.", "Presten atención a que el interés y el cuidado sean mutuos."]
    else:
        verdes = ["Las diferencias pueden abrir conversaciones interesantes.", "Cada persona puede aportar una perspectiva nueva."]
        rojas = ["No confundan una lectura de juego con una señal de incompatibilidad real.", "Hablen de expectativas y respeten el ritmo de cada quien."]
    return verdes, rojas, [
        "Una caminata y café en un lugar tranquilo.",
        "Elegir una librería, feria o museo y contarse qué les llamó la atención.",
        "Preparar algo sencillo juntos y armar una playlist compartida.",
    ]


def crear_cliente_openai():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        timeout=25.0,
        max_retries=1,
    )


def instrucciones_con_vibe(instrucciones, vibe):
    return f"{instrucciones}\n{VIBE_PROMPTS[vibe]}"


def solicitar_respuesta_ia(instrucciones, mensajes):
    cliente = crear_cliente_openai()
    if cliente is None:
        return None, (jsonify({
            "error": "La IA todavía no está configurada. Añade OPENAI_API_KEY a las variables de entorno del servidor."
        }), 503)

    modelo = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
    try:
        respuesta = cliente.responses.create(
            model=modelo,
            instructions=instrucciones,
            input=mensajes,
            max_output_tokens=650,
            store=False,
        )
    except OpenAIError:
        app.logger.exception("Falló una solicitud al servicio de IA.")
        return None, (jsonify({
            "error": "No pudimos conectar con la IA ahora. Inténtalo de nuevo en unos momentos."
        }), 502)

    contenido = respuesta.output_text
    if not contenido or not contenido.strip():
        app.logger.error("El servicio de IA devolvió una respuesta vacía.")
        return None, (jsonify({
            "error": "La IA no generó una respuesta. Inténtalo de nuevo."
        }), 502)
    return contenido.strip(), None


def texto_de_campo(datos, campo, limite=500):
    valor = datos.get(campo, "")
    return valor.strip()[:limite] if isinstance(valor, str) else ""


def construir_contexto_lectura(modo, resultado):
    lineas = [f"Modo: {READING_PROMPTS[modo]}."]
    nombres = resultado.get("nombres")
    if isinstance(nombres, list):
        nombres_validos = [nombre.strip()[:80] for nombre in nombres[:4] if isinstance(nombre, str) and nombre.strip()]
        if nombres_validos:
            lineas.append(f"Nombres compartidos voluntariamente para esta lectura: {', '.join(nombres_validos)}.")
    resumen = texto_de_campo(resultado, "resumen", 700)
    consejo = texto_de_campo(resultado, "consejo", 500)
    if resumen:
        lineas.append(f"Resumen inicial: {resumen}")

    porcentaje = resultado.get("porcentaje")
    if isinstance(porcentaje, int) and not isinstance(porcentaje, bool) and 0 <= porcentaje <= 100:
        lineas.append(f"Porcentaje lúdico de afinidad: {porcentaje}%. Aclara que no es una medida científica.")

    lecturas = resultado.get("lecturas")
    if isinstance(lecturas, list):
        for lectura in lecturas[:4]:
            if isinstance(lectura, dict):
                titulo = texto_de_campo(lectura, "titulo", 100)
                texto = texto_de_campo(lectura, "texto", 500)
                if titulo or texto:
                    lineas.append(f"{titulo}: {texto}")

    cartas = resultado.get("cartas")
    if isinstance(cartas, list):
        for carta in cartas[:3]:
            if isinstance(carta, dict):
                posicion = texto_de_campo(carta, "posicion", 100)
                nombre = texto_de_campo(carta, "nombre", 100)
                clave = texto_de_campo(carta, "clave", 200)
                mensaje = texto_de_campo(carta, "mensaje", 400)
                if nombre or mensaje:
                    lineas.append(f"{posicion} — {nombre} ({clave}): {mensaje}")

    for campo, etiqueta in (
        ("green_flags", "Aspectos positivos para explorar"),
        ("red_flags", "Aspectos para conversar, sin asumir problemas"),
        ("apodos", "Apodos sugeridos"),
        ("planes_cita", "Planes de cita"),
    ):
        valores = resultado.get(campo)
        if isinstance(valores, list):
            fragmentos = [item.strip()[:180] for item in valores[:4] if isinstance(item, str) and item.strip()]
            if fragmentos:
                lineas.append(f"{etiqueta}: {'; '.join(fragmentos)}")

    if consejo:
        lineas.append(f"Consejo inicial: {consejo}")
    return "\n".join(lineas)


def obtener_mensaje_y_emoji(puntaje_de_amor):
    if puntaje_de_amor >= 85:
        return "¡Almas gemelas! El destino los quiere juntos. ❤️🔥", "💖"
    elif puntaje_de_amor >= 65:
        return "¡Gran compatibilidad! Hay mucha chispa entre ustedes. ✨", "😍"
    elif puntaje_de_amor >= 45:
        return "Hay potencial, pero tendrán que poner de su parte. 😉", "🙂"
    elif puntaje_de_amor >= 25:
        return "La cosa está difícil, pero en el amor nada es imposible. 😬", "😅"
    else:
        return "Mejor quédense como amigos... o ni eso. 💀", "💔"


def obtener_mensaje_segun_vibe(puntaje, vibe):
    mensaje, emoji = obtener_mensaje_y_emoji(puntaje)
    if vibe == "natural":
        return mensaje, emoji
    nivel = min(puntaje // 20, 4)
    variantes = {
        "romantico": (
            "Cada historia empieza con una chispa; dejen que la ternura marque el ritmo. 💗",
            "Puede haber una pequeña luz que merece conocerse con calma. 🌷",
            "Hay espacio para que crezca algo bonito, paso a paso. 💞",
            "Se siente una conexión especial; cuídenla con honestidad. ✨",
            "Una energía de cuento, siempre que ambos escriban la historia. 💖",
        ),
        "comico": (
            "Las estrellas están en reunión y aún no llegan a un acuerdo. 😂",
            "Hay potencial, pero quizá primero negocien quién elige la película. 🍿",
            "Buena química; ahora falta sobrevivir a elegir dónde comer. 😄",
            "La compatibilidad viene fuerte, casi para compartir las papas. 🍟",
            "Match potente: que alguien avise a la comedia romántica. 🎬",
        ),
        "mistico": (
            "El cosmos sugiere curiosidad, no una profecía. 🔮",
            "Una pequeña señal simbólica invita a escuchar y observar. 🌙",
            "Los astros imaginarios apuntan a una energía interesante. ✨",
            "Las constelaciones juegan a favor; las decisiones son de ustedes. 🌌",
            "Alineación cósmica de juego: que la realidad la escriban juntos. 🪐",
        ),
        "directo": (
            "Por ahora, chispa discreta. Si interesa, toca conversar. 😉",
            "Hay algo de química. Mejor comprobarlo con una buena charla. 😏",
            "Pinta bien: sé claro, amable y mira si hay reciprocidad. 🔥",
            "La chispa está; ahora importan el respeto y las ganas de ambos. 🌶️",
            "Match alto. Coquetea con gracia y deja espacio para un sí genuino. 💋",
        ),
    }
    return variantes[vibe][nivel], emoji

@app.route("/")
def inicio():
    return render_template("index.html")


@app.get("/manifest.webmanifest")
def manifiesto_pwa():
    return app.response_class(
        json.dumps({
            "name": "Entre Corazones",
            "short_name": "Corazones",
            "description": "Juegos, lecturas simbólicas y conversaciones para el corazón.",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#fff8f8",
            "theme_color": "#fff7f7",
            "icons": [{"src": "/app-icon.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
        }, ensure_ascii=False),
        mimetype="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/service-worker.js")
def service_worker():
    script = """
const CACHE = "entre-corazones-shell-v1";
const SHELL = ["/", "/manifest.webmanifest", "/og-card.png", "/app-icon.png"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put("/", copy));
      return response;
    }).catch(() => caches.match("/")));
    return;
  }
  event.respondWith(caches.match(request).then(cached => cached || fetch(request)));
});
"""
    return Response(
        script,
        mimetype="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@app.get("/app-icon.png")
def icono_pwa():
    imagen = Image.new("RGB", (512, 512), "#fff5f7")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((24, 24, 488, 488), radius=112, fill="#f9e5eb")
    dibujo.ellipse((122, 136, 268, 282), fill="#c84470")
    dibujo.ellipse((244, 136, 390, 282), fill="#c84470")
    dibujo.polygon(((122, 210), (390, 210), (256, 390)), fill="#c84470")
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return app.response_class(salida.getvalue(), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})


@lru_cache(maxsize=1)
def generar_imagen_open_graph():
    imagen = Image.new("RGB", (1200, 630), "#fff5f7")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((42, 42, 1158, 588), radius=42, fill="#ffffff", outline="#f0d9e1", width=3)
    dibujo.ellipse((500, 105, 700, 305), fill="#f9e5eb")
    fuente_disponible = next(
        (
            ruta for ruta in (
                "C:\\Windows\\Fonts\\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            )
            if os.path.exists(ruta)
        ),
        None,
    )
    fuente_titulo = ImageFont.truetype(fuente_disponible, 62) if fuente_disponible else ImageFont.load_default(size=42)
    fuente_texto = ImageFont.truetype(fuente_disponible, 28) if fuente_disponible else ImageFont.load_default(size=20)
    dibujo.ellipse((548, 154, 603, 209), fill="#c84470")
    dibujo.ellipse((597, 154, 652, 209), fill="#c84470")
    dibujo.polygon(((548, 185), (652, 185), (600, 249)), fill="#c84470")
    dibujo.text((600, 362), "Entre Corazones", anchor="mm", fill="#3c2b39", font=fuente_titulo)
    dibujo.text((600, 430), "Juegos, lecturas y conversaciones para el corazón", anchor="mm", fill="#897b87", font=fuente_texto)
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


@app.route("/og-card.png")
def imagen_open_graph():
    return app.response_class(
        generar_imagen_open_graph(),
        mimetype="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route("/api/calcular", methods=["POST"])
@limiter.limit("60 per minute; 500 per day")
def calcular():
    datos = obtener_datos_json()
    nombre1 = str(datos.get("nombre1", "")).strip()
    nombre2 = str(datos.get("nombre2", "")).strip()
    vibe = datos.get("vibe", "natural")

    if not nombre1 or not nombre2:
        return jsonify({"error": "Por favor escribe ambos nombres"}), 400
    if not isinstance(vibe, str) or vibe not in VIBE_PROMPTS:
        return jsonify({"error": "Elige un estilo de lectura válido."}), 400

    if len(nombre1) > 80 or len(nombre2) > 80:
        return jsonify({"error": "Cada nombre debe tener 80 caracteres o menos."}), 400
    fecha1_raw, fecha2_raw = datos.get("fecha1"), datos.get("fecha2")
    signo1_raw, signo2_raw = datos.get("signo1", ""), datos.get("signo2", "")
    if bool(fecha1_raw) != bool(fecha2_raw):
        return jsonify({"error": "Indica ambas fechas de nacimiento o deja las dos vacías."}), 400
    if bool(signo1_raw) != bool(signo2_raw):
        return jsonify({"error": "Indica ambos signos o deja los dos vacíos."}), 400

    respuesta_precalculada = COMMON_MATCHES.get(clave_par_normalizada(nombre1, nombre2))
    puntaje_nombres = (
        respuesta_precalculada["porcentaje"]
        if respuesta_precalculada
        else calculadora_de_amor(nombre1, nombre2)
    )
    dimensiones = [{"nombre": "Afinidad de nombres", "valor": puntaje_nombres}]
    lecturas = []
    puntaje_de_amor = puntaje_nombres
    if fecha1_raw and fecha2_raw:
        try:
            signo1, signo2 = obtener_signo(validar_fecha(fecha1_raw, nombre1)), obtener_signo(validar_fecha(fecha2_raw, nombre2))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
    elif signo1_raw and signo2_raw:
        signos_validos = {signo[0] for signo in SIGNOS}
        if not isinstance(signo1_raw, str) or not isinstance(signo2_raw, str) or signo1_raw not in signos_validos or signo2_raw not in signos_validos:
            return jsonify({"error": "Elige dos signos del zodíaco válidos."}), 400
        signo1, signo2 = signo1_raw, signo2_raw
    else:
        signo1 = signo2 = None
    if signo1 and signo2:
        puntos_astrologicos, lectura_astrologica = compatibilidad_signos(signo1, signo2)
        puntaje_de_amor = round(.65 * puntaje_nombres + .35 * puntos_astrologicos)
        dimensiones.append({"nombre": "Astrología ligera", "valor": puntos_astrologicos})
        lecturas.append({
            "titulo": "Astrología ligera",
            "texto": f"{nombre1} ({signo1}) y {nombre2} ({signo2}): {lectura_astrologica} Es una mirada simbólica, no una predicción.",
        })
    mensaje, emoji = obtener_mensaje_segun_vibe(puntaje_de_amor, vibe)
    if respuesta_precalculada and not fecha1_raw and not signo1_raw and vibe == "natural":
        mensaje = respuesta_precalculada["mensaje"]
    verdes, rojas, planes = extras_de_match(puntaje_de_amor)
    registrar_metrica(match=True, score=puntaje_de_amor)

    return jsonify({
        "porcentaje": puntaje_de_amor,
        "mensaje": mensaje,
        "emoji": emoji,
        "titulo": "Su match de nombres",
        "resumen": mensaje,
        "consejo": "Tómalo como un juego: lo que construyan depende de cómo se escuchan y se tratan.",
        "dimensiones": dimensiones,
        "lecturas": lecturas,
        "green_flags": verdes,
        "red_flags": rojas,
        "apodos": calcular_apodos(nombre1, nombre2),
        "planes_cita": planes,
        "respuesta_precalculada": bool(respuesta_precalculada and not fecha1_raw and not signo1_raw),
    })


@app.get("/api/celebridades")
def listar_celebridades():
    return jsonify({"opciones": [{"nombre": nombre, "tipo": tipo} for nombre, tipo in CELEBRITIES]})


@app.post("/api/match-celebridad")
@limiter.limit("60 per minute; 500 per day")
def match_celebridad():
    datos = obtener_datos_json()
    nombre = texto_de_campo(datos, "nombre", 80)
    opciones = datos.get("opciones")
    if not nombre:
        return jsonify({"error": "Escribe tu nombre para calcular el match."}), 400
    if not isinstance(opciones, list) or not 1 <= len(opciones) <= len(CELEBRITIES):
        return jsonify({"error": "Elige al menos una celebridad o personaje."}), 400
    permitidas = {opcion[0]: opcion[1] for opcion in CELEBRITIES}
    if any(not isinstance(item, str) or item not in permitidas for item in opciones):
        return jsonify({"error": "La lista contiene una opción no válida."}), 400
    ranking = sorted(
        ({"nombre": persona, "tipo": permitidas[persona], "porcentaje": calculadora_de_amor(nombre, persona)}
         for persona in set(opciones)),
        key=lambda item: (-item["porcentaje"], item["nombre"]),
    )
    registrar_metrica(match=True, score=ranking[0]["porcentaje"])
    return jsonify({
        "titulo": "Tu química de ficción",
        "resumen": f"Tu mayor química simbólica fue con {ranking[0]['nombre']}. ¡Puro juego!",
        "porcentaje": ranking[0]["porcentaje"],
        "ranking": ranking,
        "green_flags": ["La imaginación hace divertido comparar estilos.", "La ficción puede dar pie a una buena conversación."],
        "red_flags": ["No es una predicción sobre relaciones reales.", "Una persona famosa o un personaje no puede dar consentimiento a un match real."],
        "planes_cita": ["Maratón de su serie o película favorita.", "Un plan inspirado en el universo del personaje.", "Crear juntos una playlist para esa historia."],
    })


@app.post("/api/ranking")
@limiter.limit("60 per minute; 500 per day")
def ranking_match():
    datos = obtener_datos_json()
    nombre = texto_de_campo(datos, "nombre", 80)
    opciones = datos.get("opciones")
    if not nombre or not isinstance(opciones, list) or not 3 <= len(opciones) <= 4:
        return jsonify({"error": "Escribe tu nombre y entre 3 y 4 opciones."}), 400
    nombres = [item.strip() for item in opciones if isinstance(item, str) and item.strip()]
    if len(nombres) != len(opciones) or len(set(nombres)) != len(nombres) or any(len(item) > 80 for item in nombres):
        return jsonify({"error": "Cada opción debe ser un nombre válido de hasta 80 caracteres."}), 400
    ranking = sorted(
        ({"nombre": persona, "porcentaje": calculadora_de_amor(nombre, persona)} for persona in set(nombres)),
        key=lambda item: (-item["porcentaje"], item["nombre"]),
    )
    registrar_metrica(match=True, score=ranking[0]["porcentaje"])
    return jsonify({
        "titulo": "Desafío: 1 contra todos",
        "resumen": f"En este juego, {ranking[0]['nombre']} quedó en primer lugar.",
        "porcentaje": ranking[0]["porcentaje"],
        "ranking": ranking,
        "green_flags": ["Comparar afinidades puede ser una excusa divertida para conversar.", "Cada conexión es distinta."],
        "red_flags": ["No uses el ranking para presionar a nadie.", "El porcentaje es aleatorio en espíritu y no mide una relación."],
        "planes_cita": ["Una merienda grupal para conocerse sin presión.", "Una trivia amistosa en equipos.", "Elegir un plan sencillo que todos puedan disfrutar."],
    })


@app.post("/api/match-aleatorio")
@limiter.limit("60 per minute; 500 per day")
def match_aleatorio():
    datos = obtener_datos_json()
    opciones = ("Alex", "Sam", "Sol", "Noa", "Dani", "Cris", "Río", "Ari")
    nombre1 = texto_de_campo(datos, "nombre", 80) or random.choice(opciones)
    nombre2 = random.choice([nombre for nombre in opciones if nombre.casefold() != nombre1.casefold()])
    puntaje = calculadora_de_amor(nombre1, nombre2)
    mensaje, emoji = obtener_mensaje_segun_vibe(puntaje, "comico")
    registrar_metrica(match=True, score=puntaje)
    return jsonify({
        "titulo": "Prueba tu suerte",
        "resumen": f"{mensaje} En una comedia romántica imaginaria, {nombre1} y {nombre2} se conocen discutiendo por la última empanada.",
        "porcentaje": puntaje,
        "emoji": emoji,
        "green_flags": ["La historia empezó con humor.", "Una empanada compartida puede ser un gran comienzo de ficción."],
        "red_flags": ["La última empanada es un asunto serio.", "Esta pareja inventada no predice nada."],
        "apodos": calcular_apodos(nombre1, nombre2),
        "planes_cita": ["Compartir una merienda.", "Inventar el final de la comedia romántica.", "Hacer una playlist de canciones dramáticas."],
        "nombres": [nombre1, nombre2],
    })


@app.post("/api/historia-aleatoria")
@limiter.limit("5 per minute; 20 per day")
def historia_aleatoria():
    datos = obtener_datos_json()
    nombres = datos.get("nombres")
    if not isinstance(nombres, list) or len(nombres) != 2 or any(
        not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 80
        for nombre in nombres
    ):
        return jsonify({"error": "La combinación aleatoria enviada no es válida."}), 400
    instrucciones = (
        LOVE_CHAT_PROMPT
        + " Inventa una microhistoria romántica y absurda de 3 a 5 frases con humor amable. "
        "No la presentes como una predicción ni como un hecho real. No incluyas contenido sexual explícito."
    )
    historia, error = solicitar_respuesta_ia(
        instrucciones,
        [{"role": "user", "content": f"Protagonistas de ficción para este juego: {nombres[0].strip()} y {nombres[1].strip()}."}],
    )
    if error:
        return error
    if len(historia) > 1200:
        historia = historia[:1200]
    registrar_metrica()
    return jsonify({"historia": historia})


@app.post("/api/idea-ranking")
@limiter.limit("5 per minute; 20 per day")
def idea_ranking():
    datos = obtener_datos_json()
    ranking = datos.get("ranking")
    if not isinstance(ranking, list) or not 3 <= len(ranking) <= 4 or any(
        not isinstance(item, dict)
        or not isinstance(item.get("nombre"), str)
        or not item["nombre"].strip()
        or len(item["nombre"]) > 80
        or isinstance(item.get("porcentaje"), bool)
        or not isinstance(item.get("porcentaje"), int)
        or not 0 <= item["porcentaje"] <= 100
        for item in ranking
    ):
        return jsonify({"error": "El ranking enviado no es válido."}), 400
    resumen = "\n".join(f"{indice}. {item['nombre'].strip()}: {item['porcentaje']}%" for indice, item in enumerate(ranking, start=1))
    instrucciones = (
        LOVE_CHAT_PROMPT
        + " Comenta en 2 o 3 frases un ranking recreativo calculado por juego de nombres. "
        "No alteres el orden, no afirmes conocer sentimientos ni compatibilidad real y no sugieras "
        "competir por el afecto de nadie. Mantén el tono ligero y amable."
    )
    comentario, error = solicitar_respuesta_ia(
        instrucciones,
        [{"role": "user", "content": f"Ranking de juego:\n{resumen}"}],
    )
    if error:
        return error
    registrar_metrica()
    return jsonify({"comentario": comentario[:800]})


@app.post("/api/ideas-ia")
@limiter.limit("5 per minute; 20 per day")
def ideas_ia():
    datos = obtener_datos_json()
    modo = datos.get("modo", "names")
    resultado = datos.get("resultado")
    if not isinstance(modo, str) or modo not in READING_PROMPTS or not isinstance(resultado, dict):
        return jsonify({"error": "La lectura enviada no es válida."}), 400
    contexto = construir_contexto_lectura(modo, resultado)
    if len(contexto) > 5000:
        return jsonify({"error": "La lectura contiene demasiada información."}), 400
    instrucciones = (
        "Responde exclusivamente con un objeto JSON válido, sin bloque markdown, con las claves "
        '"green_flags", "red_flags", "apodos" y "planes_cita". Devuelve exactamente 2 elementos '
        "en cada lista de flags, 4 apodos breves y 3 planes de cita concretos, económicos y seguros. "
        "No afirmes conocer sentimientos de terceros ni presentes la lectura como evidencia. "
        "Las red flags deben ser preguntas o aspectos a conversar, no acusaciones. Mantén todo en español. "
        + LOVE_CHAT_PROMPT
    )
    contenido, error = solicitar_respuesta_ia(instrucciones, [{"role": "user", "content": contexto}])
    if error:
        return error
    try:
        resultado_ia = json.loads(contenido)
    except json.JSONDecodeError:
        app.logger.error("La IA devolvió extras de lectura en un formato distinto a JSON.")
        return jsonify({"error": "La IA no pudo preparar las ideas en el formato esperado. Inténtalo de nuevo."}), 502
    listas = ("green_flags", "red_flags", "apodos", "planes_cita")
    if not isinstance(resultado_ia, dict) or any(
        not isinstance(resultado_ia.get(campo), list)
        or len(resultado_ia[campo]) != cantidad
        or any(not isinstance(texto, str) or not texto.strip() or len(texto) > 240 for texto in resultado_ia[campo])
        for campo, cantidad in zip(listas, (2, 2, 4, 3))
    ):
        app.logger.error("La IA devolvió una estructura incompleta para los extras de lectura.")
        return jsonify({"error": "La IA no pudo preparar las ideas en el formato esperado. Inténtalo de nuevo."}), 502
    return jsonify({campo: [texto.strip() for texto in resultado_ia[campo]] for campo in listas})


@app.post("/api/feedback")
@limiter.limit("20 per minute; 100 per day")
def feedback_lectura():
    datos = obtener_datos_json()
    modo, rating = datos.get("modo"), datos.get("rating")
    if not isinstance(modo, str) or modo not in READING_PROMPTS or isinstance(rating, bool) or not isinstance(rating, int) or rating not in (-1, 1):
        return jsonify({"error": "La valoración enviada no es válida."}), 400
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_feedback (metric_date, mode, rating, total)
                VALUES (CURRENT_DATE, %s, %s, 1)
                ON CONFLICT (metric_date, mode, rating) DO UPDATE SET total = daily_feedback.total + 1
                """,
                (modo, rating),
            )
    except (psycopg.Error, RuntimeError) as error:
        return respuesta_base_datos_no_disponible(error)
    return jsonify({"ok": True})


@app.get("/api/community")
@limiter.limit("30 per minute")
def comunidad():
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT pair_id, vote, count(*) FROM community_votes WHERE pair_id <> %s "
                "GROUP BY pair_id, vote",
                ("__seed__",),
            )
            conteos = {}
            for pair_id, voto, total in cursor.fetchall():
                conteos.setdefault(pair_id, {True: 0, False: 0})[voto] = total
    except (psycopg.Error, RuntimeError) as error:
        return respuesta_base_datos_no_disponible(error)
    return jsonify({"pares": [
        {"id": pair_id, "nombre": info[0], "descripcion": info[1],
         "si": conteos.get(pair_id, {}).get(True, 0), "no": conteos.get(pair_id, {}).get(False, 0)}
        for pair_id, info in COMMUNITY_PAIRS.items()
    ]})


@app.post("/api/community/vote")
@limiter.limit("10 per minute; 40 per day")
def votar_comunidad():
    datos = obtener_datos_json()
    pair_id, vote, token = datos.get("id"), datos.get("voto"), datos.get("token")
    if pair_id not in COMMUNITY_PAIRS or not isinstance(vote, bool):
        return jsonify({"error": "El voto enviado no es válido."}), 400
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", token):
        return jsonify({"error": "No se pudo identificar tu voto anónimo. Recarga la página."}), 400
    token_salt = os.getenv("COMMUNITY_VOTE_SALT", "").strip()
    if not token_salt:
        return jsonify({"error": "La votación no está configurada: falta COMMUNITY_VOTE_SALT en el servidor."}), 503
    token_hash = hmac.new(token_salt.encode(), f"{pair_id}:{token}".encode(), hashlib.sha256).hexdigest()
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO community_votes (pair_id, voter_hash, vote) VALUES (%s, %s, %s) "
                "ON CONFLICT (pair_id, voter_hash) DO UPDATE SET vote = EXCLUDED.vote, created_at = now()",
                (pair_id, token_hash, vote),
            )
    except (psycopg.Error, RuntimeError) as error:
        return respuesta_base_datos_no_disponible(error)
    return jsonify({"ok": True})


@app.get("/api/metrics")
@limiter.limit("10 per minute")
def metricas():
    esperado = os.getenv("METRICS_ADMIN_TOKEN", "")
    suministrado = request.headers.get("X-Metrics-Token", "")
    if not esperado:
        return jsonify({"error": "El dashboard está desactivado: configura METRICS_ADMIN_TOKEN."}), 503
    if not hmac.compare_digest(suministrado, esperado):
        return jsonify({"error": "No autorizado."}), 401
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(matches),0), "
                "COALESCE(ROUND(SUM(score_total)::numeric / NULLIF(SUM(matches),0)),0), "
                "COALESCE(SUM(readings),0) FROM daily_metrics "
                "WHERE metric_date >= CURRENT_DATE - INTERVAL '29 days'"
            )
            matches, promedio, lecturas = cursor.fetchone()
            cursor.execute(
                "SELECT mode, rating, SUM(total) FROM daily_feedback "
                "WHERE metric_date >= CURRENT_DATE - INTERVAL '29 days' GROUP BY mode, rating"
            )
            feedback = [{"modo": modo, "rating": rating, "total": total} for modo, rating, total in cursor.fetchall()]
            cursor.execute(
                "SELECT metric_date::text, matches, "
                "ROUND(score_total::numeric / NULLIF(matches, 0)), readings "
                "FROM daily_metrics WHERE metric_date >= CURRENT_DATE - INTERVAL '29 days' "
                "ORDER BY metric_date"
            )
            serie_diaria = [
                {"fecha": dia, "matches": cantidad, "promedio": int(media or 0), "lecturas": total_lecturas}
                for dia, cantidad, media, total_lecturas in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT pair_id, vote, count(*) FROM community_votes GROUP BY pair_id, vote"
            )
            votos = [{"id": pair_id, "voto": voto, "total": total} for pair_id, voto, total in cursor.fetchall()]
    except (psycopg.Error, RuntimeError) as error:
        return respuesta_base_datos_no_disponible(error)
    return jsonify({
        "dias": 30,
        "matches": matches,
        "promedio": int(promedio),
        "lecturas": lecturas,
        "serie_diaria": serie_diaria,
        "feedback": feedback,
        "votos_comunidad": votos,
    })


@app.route("/api/test-pareja", methods=["POST"])
@limiter.limit("60 per minute; 500 per day")
def test_pareja():
    datos = obtener_datos_json()
    nombre1 = str(datos.get("nombre1", "")).strip() or "Persona 1"
    nombre2 = str(datos.get("nombre2", "")).strip() or "Persona 2"
    preguntas = (
        ("respuesta1a", "respuesta1b", "Cuando tienen tiempo libre, ¿qué les apetece más?", "Un plan tranquilo", "Una aventura improvisada"),
        ("respuesta2a", "respuesta2b", "¿Cómo suelen demostrar cariño?", "Con palabras y conversación", "Con gestos y tiempo compartido"),
        ("respuesta3a", "respuesta3b", "Ante un desacuerdo, ¿qué les ayuda más?", "Hablarlo enseguida", "Tomarse un momento y volver al tema"),
        ("respuesta4a", "respuesta4b", "¿Qué valoran más al construir un vínculo?", "La espontaneidad y novedad", "La constancia y seguridad"),
    )
    respuestas = []
    for campo1, campo2, _, _, _ in preguntas:
        respuesta1 = datos.get(campo1)
        respuesta2 = datos.get(campo2)
        if respuesta1 not in ("a", "b") or respuesta2 not in ("a", "b"):
            return jsonify({"error": "Responde las cuatro preguntas para ambas personas."}), 400
        respuestas.append((respuesta1, respuesta2))

    afinidad = round(sum(respuesta1 == respuesta2 for respuesta1, respuesta2 in respuestas) * 100 / len(preguntas))
    lecturas = []
    for indice, ((_, _, pregunta, opcion_a, opcion_b), (respuesta1, respuesta2)) in enumerate(zip(preguntas, respuestas), start=1):
        opcion1 = opcion_a if respuesta1 == "a" else opcion_b
        opcion2 = opcion_a if respuesta2 == "a" else opcion_b
        if respuesta1 == respuesta2:
            texto = f"{nombre1} y {nombre2} eligieron lo mismo: {opcion1.lower()}. Puede ser un punto de encuentro para conversar."
        else:
            texto = f"{nombre1} prefiere {opcion1.lower()}, mientras que {nombre2} se inclina por {opcion2.lower()}. Es una diferencia para explorar, no un problema en sí."
        lecturas.append({"titulo": f"{indice}. {pregunta}", "texto": texto})

    coincidencias = sum(respuesta1 == respuesta2 for respuesta1, respuesta2 in respuestas)
    resumen = f"Coincidieron en {coincidencias} de 4 respuestas. La afinidad también se construye aprendiendo a negociar las diferencias."
    registrar_metrica(match=True, score=afinidad)
    return jsonify({
        "porcentaje": afinidad,
        "titulo": "Su test de pareja",
        "resumen": resumen,
        "dimensiones": [{"nombre": "Respuestas coincidentes", "valor": afinidad}],
        "lecturas": lecturas,
        "consejo": "Elijan una diferencia de sus respuestas y cuenten qué necesidad importante hay detrás, sin intentar cambiarse."
    })


@app.route("/api/lectura-completa", methods=["POST"])
@limiter.limit("60 per minute; 500 per day")
def lectura_completa():
    datos = obtener_datos_json()
    nombre1 = str(datos.get("nombre1", "")).strip()
    nombre2 = str(datos.get("nombre2", "")).strip()
    intereses1 = str(datos.get("intereses1", "")).strip()
    intereses2 = str(datos.get("intereses2", "")).strip()
    objetivo1 = str(datos.get("objetivo1", "")).strip()
    objetivo2 = str(datos.get("objetivo2", "")).strip()

    if not all((nombre1, nombre2, intereses1, intereses2, objetivo1, objetivo2)):
        return jsonify({"error": "Completa todos los datos para preparar la lectura."}), 400

    try:
        fecha1 = validar_fecha(datos.get("fecha1"), nombre1)
        fecha2 = validar_fecha(datos.get("fecha2"), nombre2)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    signo1, signo2 = obtener_signo(fecha1), obtener_signo(fecha2)
    puntos_astrologicos, lectura_astrologica = compatibilidad_signos(signo1, signo2)
    rasgos = {nombre: rasgo for nombre, _, _, rasgo in SIGNOS}
    puntos_objetivos = 100 if objetivo1 == objetivo2 else 65
    tokens1 = set(re.findall(r"[a-záéíóúüñ]+", intereses1.lower()))
    tokens2 = set(re.findall(r"[a-záéíóúüñ]+", intereses2.lower()))
    palabras_vacias = {"para", "como", "pero", "porque", "también", "sobre", "entre", "desde", "cuando", "donde"}
    tokens1 -= palabras_vacias
    tokens2 -= palabras_vacias
    coincidencias = tokens1 & tokens2
    union_intereses = tokens1 | tokens2
    puntos_intereses = round(100 * len(coincidencias) / len(union_intereses)) if union_intereses else 50
    puntos_nombres = calculadora_de_amor(nombre1, nombre2)
    puntaje = round(0.15 * puntos_nombres + 0.3 * puntos_astrologicos + 0.3 * puntos_objetivos + 0.25 * puntos_intereses)
    objetivo_texto = "Buscan algo parecido" if puntos_objetivos == 100 else "Tienen expectativas distintas, una buena oportunidad para conversar"
    actividades = ", ".join(sorted(coincidencias)) if coincidencias else "No aparecieron intereses escritos en común, y eso también puede ser una oportunidad para descubrir algo juntos."
    registrar_metrica(match=True, score=puntaje)

    return jsonify({
        "porcentaje": puntaje,
        "emoji": "💞" if puntaje >= 70 else "💗",
        "titulo": "Una conexión con mucho potencial" if puntaje >= 75 else "Una historia por descubrir",
        "resumen": "La afinidad se construye con curiosidad, conversación y pequeños gestos cotidianos.",
        "dimensiones": [
            {"nombre": "Energía zodiacal", "valor": puntos_astrologicos},
            {"nombre": "Expectativas", "valor": puntos_objetivos},
            {"nombre": "Intereses compartidos", "valor": puntos_intereses},
        ],
        "lecturas": [
            {"titulo": "Sus energías", "texto": f"{signo1} es {rasgos[signo1]}, mientras que {signo2} es {rasgos[signo2]}. {lectura_astrologica}"},
            {"titulo": "Lo que buscan", "texto": objetivo_texto + "."},
            {"titulo": "Un punto de encuentro", "texto": f"Entre sus intereses aparecen: {actividades}."},
        ],
        "consejo": "Prueben una actividad que disfruten los dos y conversen con honestidad sobre el tipo de vínculo que quieren construir."
    })


@app.route("/api/tarot", methods=["POST"])
@limiter.limit("60 per minute; 500 per day")
def tarot():
    datos = obtener_datos_json()
    pregunta = str(datos.get("pregunta", "")).strip()
    nombre = str(datos.get("nombre", "")).strip()
    if not pregunta:
        return jsonify({"error": "Escribe una pregunta o tema para tu lectura."}), 400
    if len(pregunta) > 180:
        return jsonify({"error": "La pregunta debe tener 180 caracteres o menos."}), 400

    cartas = random.sample(ARCANOS, 3)
    posiciones = ("Lo que traes contigo", "La energía presente", "Una posibilidad para abrirte")
    lectura = [
        {"posicion": posicion, "nombre": carta[0], "emoji": carta[1], "clave": carta[2], "mensaje": carta[3]}
        for posicion, carta in zip(posiciones, cartas)
    ]
    saludo = f"{nombre}, " if nombre else ""
    registrar_metrica()
    return jsonify({
        "titulo": "Una lectura para mirar hacia dentro",
        "resumen": f"{saludo}toma esta lectura como una invitación a reflexionar sobre: «{pregunta}»",
        "cartas": lectura,
        "consejo": "Las cartas son un recurso simbólico para explorar ideas, no predicen el futuro ni sustituyen tus propias decisiones."
    })


@app.route("/api/zodiacal", methods=["POST"])
@limiter.limit("60 per minute; 500 per day")
def zodiacal():
    datos = obtener_datos_json()
    nombre1 = str(datos.get("nombre1", "")).strip() or "Persona 1"
    nombre2 = str(datos.get("nombre2", "")).strip() or "Persona 2"
    try:
        fecha1 = validar_fecha(datos.get("fecha1"), nombre1)
        fecha2 = validar_fecha(datos.get("fecha2"), nombre2)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    signo1, signo2 = obtener_signo(fecha1), obtener_signo(fecha2)
    compatibilidad, dinamica = compatibilidad_signos(signo1, signo2)
    rasgos = {nombre: rasgo for nombre, _, _, rasgo in SIGNOS}
    registrar_metrica(match=True, score=compatibilidad)
    return jsonify({
        "porcentaje": compatibilidad,
        "signo1": signo1,
        "signo2": signo2,
        "resumen": dinamica,
        "lecturas": [
            {"titulo": f"{nombre1} · {signo1}", "texto": f"En esta lectura simbólica, {signo1} aporta una energía {rasgos[signo1]}."},
            {"titulo": f"{nombre2} · {signo2}", "texto": f"{signo2} suma una energía {rasgos[signo2]}."},
            {"titulo": "La dinámica entre ustedes", "texto": dinamica},
        ],
        "consejo": "La astrología puede ser un juego para conversar; la compatibilidad real se descubre con respeto, comunicación y tiempo."
    })


@app.errorhandler(429)
def limite_de_peticiones_excedido(error):
    return jsonify({
        "error": "Has alcanzado el límite temporal de consultas con IA. Espera un poco y vuelve a intentarlo."
    }), error.code or 429


def validar_mensajes_chat(mensajes):
    if not isinstance(mensajes, list) or not mensajes or len(mensajes) > MAX_CHAT_MESSAGES:
        return None, f"Envía entre 1 y {MAX_CHAT_MESSAGES} mensajes recientes."
    mensajes_validos = []
    for mensaje in mensajes:
        if not isinstance(mensaje, dict) or mensaje.get("role") not in ("user", "assistant"):
            return None, "La conversación contiene un mensaje con formato no válido."
        contenido = mensaje.get("content")
        if not isinstance(contenido, str) or not contenido.strip() or len(contenido) > MAX_CHAT_MESSAGE_LENGTH:
            return None, f"Cada mensaje debe tener entre 1 y {MAX_CHAT_MESSAGE_LENGTH} caracteres."
        mensajes_validos.append({"role": mensaje["role"], "content": contenido.strip()})
    if mensajes_validos[-1]["role"] != "user":
        return None, "El último mensaje debe ser tuyo para poder responder."
    return mensajes_validos, None


def transmitir_respuesta_ia(instrucciones, mensajes):
    cliente = crear_cliente_openai()
    if cliente is None:
        return None, (jsonify({
            "error": "La IA todavía no está configurada. Añade OPENAI_API_KEY a las variables de entorno del servidor."
        }), 503)
    modelo = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"

    @stream_with_context
    def eventos():
        try:
            stream = cliente.responses.create(
                model=modelo,
                instructions=instrucciones,
                input=mensajes,
                max_output_tokens=650,
                store=False,
                stream=True,
            )
            for evento in stream:
                if evento.type == "response.output_text.delta":
                    yield f"data: {json.dumps({'delta': evento.delta}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except OpenAIError:
            app.logger.exception("Falló una respuesta en streaming del servicio de IA.")
            error = {"error": "La respuesta se interrumpió. Inténtalo de nuevo en unos momentos."}
            yield f"event: error\ndata: {json.dumps(error, ensure_ascii=False)}\n\n"

    return Response(
        eventos(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    ), None


@app.route("/api/chat", methods=["POST"])
@limiter.limit("8 per minute; 40 per day")
def chat():
    datos = obtener_datos_json()
    vibe = datos.get("vibe", "natural")
    if not isinstance(vibe, str) or vibe not in VIBE_PROMPTS:
        return jsonify({"error": "Elige un estilo de respuesta válido."}), 400
    mensajes_validos, mensaje_error = validar_mensajes_chat(datos.get("mensajes"))
    if mensaje_error:
        return jsonify({"error": mensaje_error}), 400
    instrucciones = instrucciones_con_vibe(LOVE_CHAT_PROMPT, vibe)
    if datos.get("stream") is True:
        respuesta, error = transmitir_respuesta_ia(instrucciones, mensajes_validos)
        return error if error else respuesta

    respuesta, error = solicitar_respuesta_ia(instrucciones, mensajes_validos)
    if error:
        return error
    return jsonify({"respuesta": respuesta})


@app.route("/api/profundizar", methods=["POST"])
@limiter.limit("5 per minute; 20 per day")
def profundizar_lectura():
    datos = obtener_datos_json()
    modo = datos.get("modo")
    resultado = datos.get("resultado")
    pregunta = texto_de_campo(datos, "pregunta", MAX_READING_QUESTION_LENGTH)
    vibe = datos.get("vibe", "natural")
    if not isinstance(modo, str) or modo not in READING_PROMPTS or not isinstance(resultado, dict):
        return jsonify({"error": "La lectura enviada no es válida."}), 400
    if not isinstance(vibe, str) or vibe not in VIBE_PROMPTS:
        return jsonify({"error": "Elige un estilo de respuesta válido."}), 400
    contexto = construir_contexto_lectura(modo, resultado)
    if len(contexto) > 5000:
        return jsonify({"error": "La lectura contiene demasiada información."}), 400

    instrucciones = (
        LOVE_CHAT_PROMPT
        + " La persona quiere profundizar en una lectura de entretenimiento. Usa solo los datos incluidos "
        "como punto de partida, no inventes hechos sobre ella ni sobre otras personas. Entrega una "
        "interpretación cálida y concreta en 2 o 3 párrafos y termina con una pregunta de reflexión "
        "o una acción pequeña y saludable. Deja claro que cualquier porcentaje o lectura es simbólico "
        "y no determina una relación."
    )
    contenido = f"Lectura para interpretar:\n{contexto}"
    if pregunta:
        contenido += f"\nLo que quiere explorar la persona: {pregunta}"

    respuesta, error = solicitar_respuesta_ia(
        instrucciones_con_vibe(instrucciones, vibe),
        [{"role": "user", "content": contenido}],
    )
    if error:
        return error
    return jsonify({"interpretacion": respuesta})


if __name__ == "__main__":
    app.run(debug=True)