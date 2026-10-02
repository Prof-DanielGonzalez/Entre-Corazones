from ..config import READING_PROMPTS

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
