"""Contact endpoints: CRUD, search, sorting, pagination, duplicate prevention."""
import re
import sqlite3

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..utils import error, paginated_query
from ..validators import validate_contact

bp = Blueprint("contacts", __name__, url_prefix="/api/contacts")

SORT_FIELDS = {"id": "id", "name": "name COLLATE NOCASE", "email": "email",
               "company": "company COLLATE NOCASE", "created_at": "created_at"}


def _get(contact_id):
    return get_db().execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()


def _duplicate(email=None, phone=None, exclude_id=None):
    """Return a message if another contact already uses this email or phone."""
    db = get_db()
    for field, value in (("email", email), ("phone", phone)):
        if value is None:
            continue
        row = db.execute(f"SELECT id FROM contacts WHERE {field} = ? AND id IS NOT ?",
                         (value, exclude_id)).fetchone()
        if row:
            return f"A contact with this {field} already exists (id {row['id']})."
    return None


@bp.get("")
def list_contacts():
    """Search by name, email or phone (?search=). Phone matching ignores
    formatting, so "98765 43210" finds "+919876543210"."""
    term = request.args.get("search", "").strip()
    search_terms = []
    if term:
        search_terms = [("name", term), ("email", term)]
        digits = re.sub(r"[\s\-().]", "", term)
        if re.fullmatch(r"\+?[0-9]+", digits):
            search_terms.append(("phone", digits))
    result, err = paginated_query(
        "SELECT * FROM contacts",
        search_terms=search_terms,
        sort_fields=SORT_FIELDS, default_sort="name",
        filters={"company": "company"},
    )
    return err or jsonify(result)


@bp.get("/<int:contact_id>")
def get_contact(contact_id):
    row = _get(contact_id)
    return jsonify(dict(row)) if row else error(404, "Contact not found.")


@bp.post("")
def create_contact():
    clean, errors = validate_contact(request.get_json(silent=True))
    if errors:
        return error(422, "Validation failed.", errors)
    dup = _duplicate(clean["email"], clean["phone"])
    if dup:
        return error(409, dup)
    db = get_db()
    try:
        cur = db.execute(
            f"INSERT INTO contacts ({', '.join(clean)}) VALUES ({', '.join('?' * len(clean))})",
            list(clean.values()))
        db.commit()
    except sqlite3.IntegrityError:  # race condition safety net
        return error(409, "Duplicate contact.")
    return jsonify(dict(_get(cur.lastrowid))), 201


def _update(contact_id, partial):
    if _get(contact_id) is None:
        return error(404, "Contact not found.")
    clean, errors = validate_contact(request.get_json(silent=True), partial=partial)
    if errors:
        return error(422, "Validation failed.", errors)
    if not clean:
        return error(400, "No updatable fields supplied.")
    dup = _duplicate(clean.get("email"), clean.get("phone"), exclude_id=contact_id)
    if dup:
        return error(409, dup)
    db = get_db()
    try:
        db.execute(
            f"UPDATE contacts SET {', '.join(f'{k} = ?' for k in clean)}, "
            "updated_at = datetime('now') WHERE id = ?",
            [*clean.values(), contact_id])
        db.commit()
    except sqlite3.IntegrityError:
        return error(409, "Duplicate contact.")
    return jsonify(dict(_get(contact_id)))


@bp.put("/<int:contact_id>")
def replace_contact(contact_id):
    return _update(contact_id, partial=False)


@bp.patch("/<int:contact_id>")
def patch_contact(contact_id):
    return _update(contact_id, partial=True)


@bp.delete("/<int:contact_id>")
def delete_contact(contact_id):
    if _get(contact_id) is None:
        return error(404, "Contact not found.")
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()
    return "", 204
