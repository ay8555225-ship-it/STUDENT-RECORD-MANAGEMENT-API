"""Application factory for the Contact Management System."""
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import db
from .routes import contacts


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("DATABASE", "contacts.db")
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(contacts.bp)

    @app.get("/")
    def index():
        return jsonify({"name": "Contact Management System API",
                        "endpoints": ["/api/contacts"]})

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def unexpected(_e):
        return jsonify({"error": "Internal server error."}), 500

    return app
