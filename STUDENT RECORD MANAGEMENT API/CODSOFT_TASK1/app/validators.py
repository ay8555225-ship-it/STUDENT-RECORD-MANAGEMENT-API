"""Input validation. Each validator returns (clean_data, errors)."""
import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{6,18}$")
CODE_RE = re.compile(r"^[A-Za-z]{2,5}[0-9]{2,4}$")
GRADES = {"A", "B", "C", "D", "E", "F"}
STATUSES = {"enrolled", "completed", "dropped"}


def _str(data, field, errors, required, max_len=100):
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[field] = "This field is required."
        return None
    if not isinstance(value, str):
        errors[field] = "Must be a string."
        return None
    value = value.strip()
    if len(value) > max_len:
        errors[field] = f"Must be at most {max_len} characters."
        return None
    return value


def validate_student(data, partial=False):
    errors, clean = {}, {}
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}
    required = not partial

    for field in ("first_name", "last_name"):
        if field in data or required:
            v = _str(data, field, errors, required, 50)
            if v is not None:
                clean[field] = v

    if "email" in data or required:
        v = _str(data, "email", errors, required, 120)
        if v is not None:
            if EMAIL_RE.match(v):
                clean["email"] = v.lower()
            else:
                errors["email"] = "Invalid email address."

    if data.get("phone") is not None:
        v = _str(data, "phone", errors, False, 20)
        if v is not None:
            if PHONE_RE.match(v):
                clean["phone"] = v
            else:
                errors["phone"] = "Invalid phone number."

    if data.get("date_of_birth") is not None:
        v = _str(data, "date_of_birth", errors, False, 10)
        if v is not None:
            try:
                dob = date.fromisoformat(v)
                if dob >= date.today():
                    errors["date_of_birth"] = "Must be in the past."
                else:
                    clean["date_of_birth"] = v
            except ValueError:
                errors["date_of_birth"] = "Use format YYYY-MM-DD."
    return clean, errors


def validate_course(data, partial=False):
    errors, clean = {}, {}
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}
    required = not partial

    if "code" in data or required:
        v = _str(data, "code", errors, required, 10)
        if v is not None:
            if CODE_RE.match(v):
                clean["code"] = v.upper()
            else:
                errors["code"] = "Format like CS101 (2-5 letters + 2-4 digits)."

    if "title" in data or required:
        v = _str(data, "title", errors, required, 120)
        if v is not None:
            clean["title"] = v

    if data.get("description") is not None:
        v = _str(data, "description", errors, False, 500)
        if v is not None:
            clean["description"] = v

    if "credits" in data:
        c = data["credits"]
        if isinstance(c, bool) or not isinstance(c, int) or not 1 <= c <= 10:
            errors["credits"] = "Must be an integer between 1 and 10."
        else:
            clean["credits"] = c
    return clean, errors


def validate_enrollment(data, partial=False):
    errors, clean = {}, {}
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}

    for field in ("student_id", "course_id"):
        if field in data or not partial:
            v = data.get(field)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                errors[field] = "Must be a positive integer."
            else:
                clean[field] = v

    if "status" in data:
        if data["status"] not in STATUSES:
            errors["status"] = f"Must be one of {sorted(STATUSES)}."
        else:
            clean["status"] = data["status"]

    if data.get("grade") is not None:
        g = str(data["grade"]).upper()
        if g not in GRADES:
            errors["grade"] = f"Must be one of {sorted(GRADES)}."
        else:
            clean["grade"] = g
    return clean, errors
