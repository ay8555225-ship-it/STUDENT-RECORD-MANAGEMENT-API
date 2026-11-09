"""User model: all database access for the users table."""
import sqlite3

from ..db import get_db

PUBLIC_COLS = "id, name, email, created_at"


def create(name, email, password_hash):
    """Insert a user. Returns the new id, or None if the email is taken."""
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash))
        db.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_by_id(user_id):
    return get_db().execute(
        f"SELECT {PUBLIC_COLS} FROM users WHERE id = ?", (user_id,)).fetchone()


def get_by_email_with_hash(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
