"""Task model: all database access for the tasks table. Every query is scoped to a user."""
from ..db import get_db


def get(user_id, task_id):
    return get_db().execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()


def create(user_id, fields):
    db = get_db()
    cols = ["user_id", *fields]
    cur = db.execute(
        f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        [user_id, *fields.values()])
    if fields.get("status") == "completed":
        db.execute("UPDATE tasks SET completed_at = datetime('now') WHERE id = ?", (cur.lastrowid,))
    db.commit()
    return cur.lastrowid


def update(user_id, task_id, fields):
    """Update fields; keeps completed_at in sync with status."""
    sets = [f"{k} = ?" for k in fields]
    if fields.get("status") == "completed":
        sets.append("completed_at = COALESCE(completed_at, datetime('now'))")
    elif fields.get("status") == "pending":
        sets.append("completed_at = NULL")
    sets.append("updated_at = datetime('now')")
    db = get_db()
    db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
               [*fields.values(), task_id, user_id])
    db.commit()


def delete(user_id, task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    db.commit()
