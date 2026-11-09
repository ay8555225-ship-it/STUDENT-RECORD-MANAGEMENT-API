"""Enrollment endpoints: CRUD linking students to courses."""
import sqlite3

from flask import Blueprint, jsonify

from ..db import get_db
from ..utils import error, get_json, paginated_query
from ..validators import validate_enrollment

bp = Blueprint("enrollments", __name__, url_prefix="/api/enrollments")

BASE_SQL = """
SELECT e.id, e.student_id, e.course_id, e.status, e.grade, e.enrolled_on,
       s.first_name || ' ' || s.last_name AS student_name,
       c.code AS course_code, c.title AS course_title
FROM enrollments e
JOIN students s ON s.id = e.student_id
JOIN courses  c ON c.id = e.course_id
"""
SORT_FIELDS = {"id": "e.id", "enrolled_on": "e.enrolled_on", "status": "e.status",
               "grade": "e.grade", "student_name": "student_name",
               "course_code": "c.code"}


def _get(enrollment_id):
    return get_db().execute(BASE_SQL + " WHERE e.id = ?", (enrollment_id,)).fetchone()


@bp.get("")
def list_enrollments():
    result, err = paginated_query(
        BASE_SQL, [],
        search_cols=["s.first_name", "s.last_name", "c.code", "c.title"],
        sort_fields=SORT_FIELDS, default_sort="id",
        filters={"student_id": "e.student_id", "course_id": "e.course_id",
                 "status": "e.status", "grade": "e.grade"},
    )
    return err or jsonify(result)


@bp.get("/<int:enrollment_id>")
def get_enrollment(enrollment_id):
    row = _get(enrollment_id)
    return jsonify(dict(row)) if row else error(404, "Enrollment not found.")


@bp.post("")
def create_enrollment():
    clean, errors = validate_enrollment(get_json())
    if errors:
        return error(422, "Validation failed.", errors)
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE id = ?", (clean["student_id"],)).fetchone() is None:
        return error(404, "Student not found.")
    if db.execute("SELECT 1 FROM courses WHERE id = ?", (clean["course_id"],)).fetchone() is None:
        return error(404, "Course not found.")
    try:
        cur = db.execute(
            f"INSERT INTO enrollments ({', '.join(clean)}) VALUES ({', '.join('?' * len(clean))})",
            list(clean.values()))
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "Student is already enrolled in this course.")
    return jsonify(dict(_get(cur.lastrowid))), 201


@bp.patch("/<int:enrollment_id>")
@bp.put("/<int:enrollment_id>")
def update_enrollment(enrollment_id):
    """Only status and grade may change; student/course are fixed once enrolled."""
    if _get(enrollment_id) is None:
        return error(404, "Enrollment not found.")
    data = get_json()
    clean, errors = validate_enrollment(data, partial=True)
    clean.pop("student_id", None)
    clean.pop("course_id", None)
    errors.pop("student_id", None)
    errors.pop("course_id", None)
    if errors:
        return error(422, "Validation failed.", errors)
    if not clean:
        return error(400, "Provide status and/or grade to update.")
    db = get_db()
    db.execute(
        f"UPDATE enrollments SET {', '.join(f'{k} = ?' for k in clean)} WHERE id = ?",
        [*clean.values(), enrollment_id])
    db.commit()
    return jsonify(dict(_get(enrollment_id)))


@bp.delete("/<int:enrollment_id>")
def delete_enrollment(enrollment_id):
    if _get(enrollment_id) is None:
        return error(404, "Enrollment not found.")
    db = get_db()
    db.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
    db.commit()
    return "", 204
