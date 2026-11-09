"""Application factory for the To-Do List Backend."""
import os
import secrets

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import db
from .routes import auth_routes, task_routes


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("DATABASE", "todo.db")
    # Set SECRET_KEY in the environment for stable tokens. If unset, a random key is
    # generated at startup (tokens then stop working whenever the server restarts).
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["TOKEN_MAX_AGE"] = 60 * 60 * 24  # tokens valid for 24 hours
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(task_routes.bp)

    @app.get("/")
    def index():
        return jsonify({"name": "To-Do List API",
                        "endpoints": ["/api/auth/register", "/api/auth/login", "/api/tasks"]})

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def unexpected(_e):
        return jsonify({"error": "Internal server error."}), 500

    return app
