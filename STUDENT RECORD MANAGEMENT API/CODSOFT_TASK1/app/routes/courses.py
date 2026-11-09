"""Course endpoints: full CRUD + search/filter/sort/pagination."""
import sqlite3

from flask import Blueprint, jsonify

from ..db import get_db
from ..utils import error, get_json, paginated_query
from ..validators import validate_course

bp = Blueprint("courses", __name__, url_prefix="/api/courses")

SORT_FIELDS = {"id": "id", "code": "code", "title": "title", "credits": "credits",
               "created_at": "created_at"}


def _get(course_id):
    return get_db().execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()


@bp.get("")
def list_courses():
    result, err = paginated_query(
        "SELECT * FROM courses", [],
        search_cols=["code", "title", "description"],
        sort_fields=SORT_FIELDS, default_sort="code",
        filters={"credits": "credits", "code": "code"},
    )
    return err or jsonify(result)


@bp.get("/<int:course_id>")
def get_course(course_id):
    row = _get(course_id)
    if row is None:
        return error(404, "Course not found.")
    course = dict(row)
    students = get_db().execute(
        """SELECT s.id, s.first_name, s.last_name, e.status, e.grade
           FROM enrollments e JOIN students s ON s.id = e.student_id
           WHERE e.course_id = ?""", (course_id,)).fetchall()
    course["students"] = [dict(s) for s in students]
    return jsonify(course)


@bp.post("")
def create_course():
    clean, errors = validate_course(get_json())
    if errors:
        return error(422, "Validation failed.", errors)
    db = get_db()
    try:
        cur = db.execute(
            f"INSERT INTO courses ({', '.join(clean)}) VALUES ({', '.join('?' * len(clean))})",
            list(clean.values()))
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "A course with this code already exists.")
    return jsonify(dict(_get(cur.lastrowid))), 201


def _update(course_id, partial):
    if _get(course_id) is None:
        return error(404, "Course not found.")
    clean, errors = validate_course(get_json(), partial=partial)
    if errors:
        return error(422, "Validation failed.", errors)
    if not clean:
        return error(400, "No updatable fields supplied.")
    db = get_db()
    try:
        db.execute(
            f"UPDATE courses SET {', '.join(f'{k} = ?' for k in clean)} WHERE id = ?",
            [*clean.values(), course_id])
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "A course with this code already exists.")
    return jsonify(dict(_get(course_id)))


@bp.put("/<int:course_id>")
def replace_course(course_id):
    return _update(course_id, partial=False)


@bp.patch("/<int:course_id>")
def patch_course(course_id):
    return _update(course_id, partial=True)


@bp.delete("/<int:course_id>")
def delete_course(course_id):
    if _get(course_id) is None:
        return error(404, "Course not found.")
    db = get_db()
    db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    db.commit()
    return "", 204
