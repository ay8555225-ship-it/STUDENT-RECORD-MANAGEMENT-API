"""URL routing for tasks. All task routes require authentication."""
from flask import Blueprint

from ..auth import login_required
from ..controllers import task_controller as ctrl

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")
bp.before_request(login_required(lambda: None))  # reject unauthenticated requests early

bp.get("")(ctrl.list_tasks)
bp.post("")(ctrl.create_task)
bp.get("/<int:task_id>")(ctrl.get_task)
bp.put("/<int:task_id>")(ctrl.replace_task)
bp.patch("/<int:task_id>")(ctrl.patch_task)
bp.delete("/<int:task_id>")(ctrl.delete_task)


@bp.patch("/<int:task_id>/complete")
def complete(task_id):
    return ctrl.set_status(task_id, "completed")


@bp.patch("/<int:task_id>/pending")
def pending(task_id):
    return ctrl.set_status(task_id, "pending")
