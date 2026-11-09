"""Request validation. Each validator returns (clean_data, errors)."""
import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUSES = {"pending", "completed"}
PRIORITIES = {"low", "medium", "high"}


def _text(data, field, errors, required, max_len):
    v = data.get(field)
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            errors[field] = "This field is required."
        return None
    if not isinstance(v, str):
        errors[field] = "Must be a string."
        return None
    v = v.strip()
    if len(v) > max_len:
        errors[field] = f"Must be at most {max_len} characters."
        return None
    return v


def is_iso_date(value):
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_register(data):
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}
    errors, clean = {}, {}
    name = _text(data, "name", errors, True, 80)
    if name:
        clean["name"] = name
    email = _text(data, "email", errors, True, 120)
    if email:
        if EMAIL_RE.match(email):
            clean["email"] = email.lower()
        else:
            errors["email"] = "Invalid email address."
    pw = data.get("password")
    if not isinstance(pw, str) or not 8 <= len(pw) <= 128:
        errors["password"] = "Must be a string of 8-128 characters."
    else:
        clean["password"] = pw
    return clean, errors


def validate_task(data, partial=False):
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}
    errors, clean = {}, {}
    required = not partial

    if "title" in data or required:
        v = _text(data, "title", errors, required, 150)
        if v is not None:
            clean["title"] = v

    for field, limit in (("description", 1000), ("category", 50)):
        if field in data:
            clean[field] = _text(data, field, errors, False, limit)  # None clears it

    if "status" in data:
        if data["status"] in STATUSES:
            clean["status"] = data["status"]
        else:
            errors["status"] = f"Must be one of {sorted(STATUSES)}."

    if "priority" in data:
        if data["priority"] in PRIORITIES:
            clean["priority"] = data["priority"]
        else:
            errors["priority"] = f"Must be one of {sorted(PRIORITIES)}."

    if "due_date" in data:
        v = data["due_date"]
        if v is None:
            clean["due_date"] = None
        elif isinstance(v, str) and is_iso_date(v):
            clean["due_date"] = v
        else:
            errors["due_date"] = "Use format YYYY-MM-DD."
    return clean, errors
