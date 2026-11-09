"""Task controller: request handling logic for task endpoints."""
from flask import g, jsonify, request

from ..models import task_model
from ..utils import error, list_query
from ..validators import is_iso_date, validate_task

SORT_FIELDS = {"id": "id", "title": "title COLLATE NOCASE", "due_date": "due_date",
               "priority": "CASE priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END",
               "created_at": "created_at", "status": "status"}


def _find(task_id):
    return task_model.get(g.user["id"], task_id)


def list_tasks():
    for param in ("due_before", "due_after"):
        if request.args.get(param) and not is_iso_date(request.args[param]):
            return error(400, f"{param} must be YYYY-MM-DD.")
    status = request.args.get("status")
    if status and status not in ("pending", "completed"):
        return error(400, "status must be 'pending' or 'completed'.")

    result, err = list_query(
        "SELECT * FROM tasks",
        scope_sql="user_id = ?", scope_args=[g.user["id"]],
        search_cols=["title", "description"],
        sort_fields=SORT_FIELDS, default_sort="-created_at",
        filters={"status": "status", "priority": "priority", "category": "category"},
        ranges={"due_before": ("due_date", "<="), "due_after": ("due_date", ">=")},
    )
    return err or jsonify(result)


def get_task(task_id):
    row = _find(task_id)
    return jsonify(dict(row)) if row else error(404, "Task not found.")


def create_task():
    clean, errors = validate_task(request.get_json(silent=True))
    if errors:
        return error(422, "Validation failed.", errors)
    task_id = task_model.create(g.user["id"], clean)
    return jsonify(dict(_find(task_id))), 201


def _update(task_id, partial):
    if _find(task_id) is None:
        return error(404, "Task not found.")
    clean, errors = validate_task(request.get_json(silent=True), partial=partial)
    if errors:
        return error(422, "Validation failed.", errors)
    if not clean:
        return error(400, "No updatable fields supplied.")
    task_model.update(g.user["id"], task_id, clean)
    return jsonify(dict(_find(task_id)))


def replace_task(task_id):
    return _update(task_id, partial=False)


def patch_task(task_id):
    return _update(task_id, partial=True)


def set_status(task_id, status):
    if _find(task_id) is None:
        return error(404, "Task not found.")
    task_model.update(g.user["id"], task_id, {"status": status})
    return jsonify(dict(_find(task_id)))


def delete_task(task_id):
    if _find(task_id) is None:
        return error(404, "Task not found.")
    task_model.delete(g.user["id"], task_id)
    return "", 204
