"""Application factory for the Student Record Management API."""
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import db
from .routes import courses, enrollments, students


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = os.environ.get("DATABASE", "students.db")
    if config:
        app.config.update(config)

    db.init_app(app)
    for module in (students, courses, enrollments):
        app.register_blueprint(module.bp)

    @app.get("/")
    def index():
        return jsonify({
            "name": "Student Record Management API",
            "endpoints": ["/api/students", "/api/courses", "/api/enrollments"],
        })

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def unexpected(_e):
        return jsonify({"error": "Internal server error."}), 500

    return app
