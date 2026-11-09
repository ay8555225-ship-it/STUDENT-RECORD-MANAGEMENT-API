"""Auth controller: request handling logic for registration and login."""
from flask import g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import create_token
from ..models import user_model
from ..utils import error
from ..validators import validate_register


def register():
    clean, errors = validate_register(request.get_json(silent=True))
    if errors:
        return error(422, "Validation failed.", errors)
    user_id = user_model.create(
        clean["name"], clean["email"], generate_password_hash(clean["password"]))
    if user_id is None:
        return error(409, "An account with this email already exists.")
    user = dict(user_model.get_by_id(user_id))
    return jsonify({"user": user, "token": create_token(user_id)}), 201


def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("email"), str) \
            or not isinstance(data.get("password"), str):
        return error(422, "Validation failed.", {"body": "email and password are required."})
    row = user_model.get_by_email_with_hash(data["email"].strip().lower())
    # Same message for unknown email and wrong password: avoids leaking which accounts exist.
    if row is None or not check_password_hash(row["password_hash"], data["password"]):
        return error(401, "Invalid email or password.")
    return jsonify({"token": create_token(row["id"])})


def me():
    return jsonify(dict(g.user))
