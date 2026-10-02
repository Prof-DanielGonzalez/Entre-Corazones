import hashlib
import re
from datetime import date
from functools import lru_cache

from ..config import SIGNOS

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
