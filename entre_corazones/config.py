import json
import unicodedata
from pathlib import Path

def clave_par_normalizada(nombre1, nombre2):
    partes = (
        unicodedata.normalize("NFKD", nombre1).encode("ascii", "ignore").decode("ascii").casefold().strip(),
        unicodedata.normalize("NFKD", nombre2).encode("ascii", "ignore").decode("ascii").casefold().strip(),
    )
    return "|".join(sorted(partes))

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

_COMMON_MATCHES_PATH = Path(__file__).resolve().parent.parent / "static" / "common_matches.json"

with _COMMON_MATCHES_PATH.open(encoding="utf-8") as archivo:
    COMMON_MATCHES = {
        clave_par_normalizada(item["names"][0], item["names"][1]): item
        for item in json.load(archivo)
    }
