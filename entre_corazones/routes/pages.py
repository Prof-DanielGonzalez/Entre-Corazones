import json
import os
from functools import lru_cache
from io import BytesIO

from flask import Blueprint, Response, current_app, render_template
from PIL import Image, ImageDraw, ImageFont

pages = Blueprint("pages", __name__)

@pages.route("/")
def inicio():
    return render_template("index.html")

@pages.get("/manifest.webmanifest")
def manifiesto_pwa():
    return current_app.response_class(
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

@pages.get("/service-worker.js")
def service_worker():
    script = """
const CACHE = "entre-corazones-shell-v3";
const SHELL = [
  "/",
  "/manifest.webmanifest",
  "/og-card.png",
  "/app-icon.png",
  "/static/css/app.css",
  "/static/js/app.js"
];
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

@pages.get("/app-icon.png")
def icono_pwa():
    imagen = Image.new("RGB", (512, 512), "#fff5f7")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((24, 24, 488, 488), radius=112, fill="#f9e5eb")
    dibujo.ellipse((122, 136, 268, 282), fill="#c84470")
    dibujo.ellipse((244, 136, 390, 282), fill="#c84470")
    dibujo.polygon(((122, 210), (390, 210), (256, 390)), fill="#c84470")
    salida = BytesIO()
    imagen.save(salida, format="PNG", optimize=True)
    return current_app.response_class(salida.getvalue(), mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})

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

@pages.route("/og-card.png")
def imagen_open_graph():
    return current_app.response_class(
        generar_imagen_open_graph(),
        mimetype="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
