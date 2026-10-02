import hashlib
import hmac
import json
import os
import random
import re

import psycopg
from flask import Blueprint, current_app, jsonify, request

from ..config import (
    ARCANOS,
    CELEBRITIES,
    COMMON_MATCHES,
    COMMUNITY_PAIRS,
    LOVE_CHAT_PROMPT,
    MAX_READING_QUESTION_LENGTH,
    READING_PROMPTS,
    SIGNOS,
    VIBE_PROMPTS,
    clave_par_normalizada,
)
from ..extensions import limiter
from ..infrastructure.database import (
    conectar_base_datos,
    registrar_metrica,
    respuesta_base_datos_no_disponible,
)
from ..services.ai import (
    instrucciones_con_vibe,
    solicitar_respuesta_ia,
    transmitir_respuesta_ia,
    validar_mensajes_chat,
)
from ..services.domain import (
    calcular_apodos,
    calculadora_de_amor,
    compatibilidad_signos,
    extras_de_match,
    obtener_signo,
    validar_fecha,
)
from ..services.readings import (
    construir_contexto_lectura,
    obtener_mensaje_segun_vibe,
    texto_de_campo,
)

api = Blueprint("api", __name__)


def obtener_datos_json():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


@api.route("/api/calcular", methods=["POST"])

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

@api.get("/api/celebridades")
def listar_celebridades():
    return jsonify({"opciones": [{"nombre": nombre, "tipo": tipo} for nombre, tipo in CELEBRITIES]})

@api.post("/api/match-celebridad")

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

@api.post("/api/ranking")

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

@api.post("/api/match-aleatorio")

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

@api.post("/api/historia-aleatoria")

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

@api.post("/api/idea-ranking")

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

@api.post("/api/ideas-ia")

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
        current_app.logger.error("La IA devolvió extras de lectura en un formato distinto a JSON.")
        return jsonify({"error": "La IA no pudo preparar las ideas en el formato esperado. Inténtalo de nuevo."}), 502
    listas = ("green_flags", "red_flags", "apodos", "planes_cita")
    if not isinstance(resultado_ia, dict) or any(
        not isinstance(resultado_ia.get(campo), list)
        or len(resultado_ia[campo]) != cantidad
        or any(not isinstance(texto, str) or not texto.strip() or len(texto) > 240 for texto in resultado_ia[campo])
        for campo, cantidad in zip(listas, (2, 2, 4, 3))
    ):
        current_app.logger.error("La IA devolvió una estructura incompleta para los extras de lectura.")
        return jsonify({"error": "La IA no pudo preparar las ideas en el formato esperado. Inténtalo de nuevo."}), 502
    return jsonify({campo: [texto.strip() for texto in resultado_ia[campo]] for campo in listas})

@api.post("/api/feedback")

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

@api.get("/api/community")

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

@api.post("/api/community/vote")

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

@api.get("/api/metrics")

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

@api.route("/api/test-pareja", methods=["POST"])

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

@api.route("/api/lectura-completa", methods=["POST"])

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

@api.route("/api/tarot", methods=["POST"])

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

@api.route("/api/zodiacal", methods=["POST"])

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

@api.route("/api/chat", methods=["POST"])

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

@api.route("/api/profundizar", methods=["POST"])

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

def limite_de_peticiones_excedido(error):
    return jsonify({
        "error": "Has alcanzado el límite temporal de consultas con IA. Espera un poco y vuelve a intentarlo."
    }), error.code or 429
