"""Token authentication using signed, expiring tokens (itsdangerous, bundled with Flask)."""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .models import user_model
from .utils import error


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="todo-auth")


def create_token(user_id):
    return _serializer().dumps({"uid": user_id})


def login_required(view):
    """Require 'Authorization: Bearer <token>'; sets g.user on success."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return error(401, "Missing or malformed Authorization header.")
        try:
            data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
        except SignatureExpired:
            return error(401, "Token has expired. Please log in again.")
        except BadSignature:
            return error(401, "Invalid token.")
        user = user_model.get_by_id(data["uid"])
        if user is None:
            return error(401, "User no longer exists.")
        g.user = user
        return view(*args, **kwargs)
    return wrapper
