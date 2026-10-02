import os
import json

from flask import Response, current_app, jsonify, stream_with_context
from openai import OpenAI, OpenAIError

from ..config import MAX_CHAT_MESSAGES, MAX_CHAT_MESSAGE_LENGTH, VIBE_PROMPTS

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
        current_app.logger.exception("Falló una solicitud al servicio de IA.")
        return None, (jsonify({
            "error": "No pudimos conectar con la IA ahora. Inténtalo de nuevo en unos momentos."
        }), 502)

    contenido = respuesta.output_text
    if not contenido or not contenido.strip():
        current_app.logger.error("El servicio de IA devolvió una respuesta vacía.")
        return None, (jsonify({
            "error": "La IA no generó una respuesta. Inténtalo de nuevo."
        }), 502)
    return contenido.strip(), None

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
            current_app.logger.exception("Falló una respuesta en streaming del servicio de IA.")
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
