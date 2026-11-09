# CODSOFT_TASK2 — Contact Management System

A REST backend (Flask + SQLite) for managing personal and professional contacts.

## Run

```bash
pip install -r requirements.txt
python run.py            # http://127.0.0.1:5000
python -m pytest         # run the test suite
```

The SQLite file `contacts.db` is created automatically (override with the `DATABASE` env var).

## Project structure

```
app/
  __init__.py        application factory, JSON error handlers
  db.py              SQLite connection + schema
  validators.py      validation and normalisation (email lower-cased, phone digits only)
  utils.py           error helper + search/filter/sort/pagination
  routes/contacts.py contact endpoints
tests/test_contacts.py
run.py
```

## Data model

**contacts** — id, name, email (unique), phone (unique), address, company, created_at, updated_at

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/contacts` | List with search, filter, sort, pagination |
| POST | `/api/contacts` | Add a contact |
| GET | `/api/contacts/<id>` | Retrieve one |
| PUT | `/api/contacts/<id>` | Replace (name, email, phone required) |
| PATCH | `/api/contacts/<id>` | Partial update |
| DELETE | `/api/contacts/<id>` | Delete |

### List query parameters

- `search=` — matches name, email or phone. Phone search ignores formatting (`98765 10002` finds `+919876510002`).
- `company=` — exact, case-insensitive filter
- `sort=field` / `sort=-field` — `id`, `name`, `email`, `company`, `created_at` (default `name`)
- `page` (default 1), `per_page` (default 10, max 100)

Response: `{"data": [...], "pagination": {"page", "per_page", "total", "pages"}}`

### Validation and duplicates

- `name` required (max 100); `email` must be valid; `phone` must be 7-15 digits with optional `+` (spaces, dashes and brackets are stripped before storing)
- Duplicates are rejected with `409` when the **email** (case-insensitive) or the **phone** (after normalising) already belongs to another contact

### Status codes

`200` OK · `201` created · `204` deleted · `400` bad query / empty update · `404` not found · `409` duplicate · `422` validation failed (field-level `details`) · `500` unexpected error

### Example

```bash
curl -X POST localhost:5000/api/contacts -H 'Content-Type: application/json' \
  -d '{"name":"Asha Verma","email":"asha@acme.com","phone":"+91 98765 43210","company":"Acme"}'

curl 'localhost:5000/api/contacts?search=asha&sort=-created_at&per_page=5'
```
