"""Student endpoints: full CRUD + search/filter/sort/pagination."""
import sqlite3

from flask import Blueprint, jsonify

from ..db import get_db
from ..utils import error, get_json, paginated_query
from ..validators import validate_student

bp = Blueprint("students", __name__, url_prefix="/api/students")

SORT_FIELDS = {"id": "id", "first_name": "first_name", "last_name": "last_name",
               "email": "email", "created_at": "created_at"}


def _get(student_id):
    return get_db().execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()


@bp.get("")
def list_students():
    result, err = paginated_query(
        "SELECT * FROM students", [],
        search_cols=["first_name", "last_name", "email"],
        sort_fields=SORT_FIELDS, default_sort="id",
        filters={"last_name": "last_name", "email": "email"},
    )
    return err or jsonify(result)


@bp.get("/<int:student_id>")
def get_student(student_id):
    row = _get(student_id)
    if row is None:
        return error(404, "Student not found.")
    student = dict(row)
    courses = get_db().execute(
        """SELECT c.id, c.code, c.title, e.status, e.grade
           FROM enrollments e JOIN courses c ON c.id = e.course_id
           WHERE e.student_id = ?""", (student_id,)).fetchall()
    student["courses"] = [dict(c) for c in courses]
    return jsonify(student)


@bp.post("")
def create_student():
    data = get_json()
    clean, errors = validate_student(data)
    if errors:
        return error(422, "Validation failed.", errors)
    db = get_db()
    try:
        cur = db.execute(
            f"INSERT INTO students ({', '.join(clean)}) VALUES ({', '.join('?' * len(clean))})",
            list(clean.values()))
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "A student with this email already exists.")
    return jsonify(dict(_get(cur.lastrowid))), 201


def _update(student_id, partial):
    if _get(student_id) is None:
        return error(404, "Student not found.")
    clean, errors = validate_student(get_json(), partial=partial)
    if errors:
        return error(422, "Validation failed.", errors)
    if not clean:
        return error(400, "No updatable fields supplied.")
    db = get_db()
    try:
        db.execute(
            f"UPDATE students SET {', '.join(f'{k} = ?' for k in clean)} WHERE id = ?",
            [*clean.values(), student_id])
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "A student with this email already exists.")
    return jsonify(dict(_get(student_id)))


@bp.put("/<int:student_id>")
def replace_student(student_id):
    return _update(student_id, partial=False)


@bp.patch("/<int:student_id>")
def patch_student(student_id):
    return _update(student_id, partial=True)


@bp.delete("/<int:student_id>")
def delete_student(student_id):
    if _get(student_id) is None:
        return error(404, "Student not found.")
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return "", 204
