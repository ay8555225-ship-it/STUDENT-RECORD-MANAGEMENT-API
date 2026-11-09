"""URL routing for authentication."""
from flask import Blueprint

from ..auth import login_required
from ..controllers import auth_controller as ctrl

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

bp.post("/register")(ctrl.register)
bp.post("/login")(ctrl.login)
bp.get("/me")(login_required(ctrl.me))
