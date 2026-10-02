import hashlib
import random
import re
from datetime import date

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


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

@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/calcular", methods=["POST"])
def calcular():
    datos = obtener_datos_json()
    nombre1 = str(datos.get("nombre1", "")).strip()
    nombre2 = str(datos.get("nombre2", "")).strip()

    if not nombre1 or not nombre2:
        return jsonify({"error": "Por favor escribe ambos nombres"}), 400

    puntaje_de_amor = calculadora_de_amor(nombre1, nombre2)
    mensaje, emoji = obtener_mensaje_y_emoji(puntaje_de_amor)

    return jsonify({"porcentaje": puntaje_de_amor, "mensaje": mensaje, "emoji": emoji})


@app.route("/api/lectura-completa", methods=["POST"])
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
    return jsonify({
        "titulo": "Una lectura para mirar hacia dentro",
        "resumen": f"{saludo}toma esta lectura como una invitación a reflexionar sobre: «{pregunta}»",
        "cartas": lectura,
        "consejo": "Las cartas son un recurso simbólico para explorar ideas, no predicen el futuro ni sustituyen tus propias decisiones."
    })


@app.route("/api/zodiacal", methods=["POST"])
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


if __name__ == "__main__":
    app.run(debug=True)