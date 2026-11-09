"""Input validation and normalisation for contacts. Returns (clean, errors)."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_phone(raw):
    """'+91 98765-43210' -> '+919876543210'. Returns None if not a valid number."""
    cleaned = re.sub(r"[\s\-().]", "", raw)
    if re.fullmatch(r"\+?[0-9]{7,15}", cleaned):
        return cleaned
    return None


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


def validate_contact(data, partial=False):
    if not isinstance(data, dict):
        return {}, {"body": "JSON object expected."}
    errors, clean = {}, {}
    required = not partial

    if "name" in data or required:
        v = _text(data, "name", errors, required, 100)
        if v is not None:
            clean["name"] = v

    if "email" in data or required:
        v = _text(data, "email", errors, required, 120)
        if v is not None:
            if EMAIL_RE.match(v):
                clean["email"] = v.lower()
            else:
                errors["email"] = "Invalid email address."

    if "phone" in data or required:
        v = _text(data, "phone", errors, required, 25)
        if v is not None:
            phone = normalize_phone(v)
            if phone:
                clean["phone"] = phone
            else:
                errors["phone"] = "Invalid phone number (7-15 digits, optional leading +)."

    for field, limit in (("address", 250), ("company", 100)):
        if field in data:
            v = _text(data, field, errors, False, limit)
            clean[field] = v  # None clears the field
    return clean, errors
