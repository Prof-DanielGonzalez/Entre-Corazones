import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import limiter
from .routes.api import api, limite_de_peticiones_excedido
from .routes.pages import pages


def create_app():
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path="/static",
        template_folder="../templates",
    )
    if os.getenv("RENDER"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
    limiter.init_app(app)
    app.register_blueprint(pages)
    app.register_blueprint(api)
    app.register_error_handler(429, limite_de_peticiones_excedido)
    return app
