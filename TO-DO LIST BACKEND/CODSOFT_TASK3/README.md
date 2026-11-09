# CODSOFT_TASK3 — To-Do List Backend

A RESTful task-management backend (Flask + SQLite) with per-user accounts.
Includes the bonus items: due dates, priority levels, categories and user authentication.

## Run

```bash
pip install -r requirements.txt
export SECRET_KEY="change-me"   # optional; random key is generated if unset
python run.py                   # http://127.0.0.1:5000
python -m pytest                # run the test suite
```

`todo.db` is created automatically (override with the `DATABASE` env var).

## Project structure

```
app/
  __init__.py                 application factory, JSON error handlers
  db.py                       SQLite connection + schema
  auth.py                     signed expiring tokens + login_required
  validators.py               request validation
  utils.py                    error helper + list/filter/sort/paginate query
  models/                     user_model.py, task_model.py   (database access)
  controllers/                auth_controller.py, task_controller.py   (logic)
  routes/                     auth_routes.py, task_routes.py   (URL mapping)
docs/todo_api.postman_collection.json   API documentation (import into Postman)
tests/test_todo.py
run.py
```

## API documentation

Import `docs/todo_api.postman_collection.json` into Postman. Run **Register** or **Login**
first; the token is stored automatically and sent with every other request.

### Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | `name`, `email`, `password` (8+ chars) → 201 + token |
| POST | `/api/auth/login` | `email`, `password` → 200 + token (valid 24 h) |
| GET | `/api/auth/me` | Current user |

Send the token as `Authorization: Bearer <token>`.

### Tasks (authentication required, each user sees only their own tasks)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/tasks` | List with filters (below) |
| POST | `/api/tasks` | `title` required; optional `description`, `priority`, `category`, `due_date` (YYYY-MM-DD), `status` |
| GET | `/api/tasks/<id>` | Retrieve |
| PUT | `/api/tasks/<id>` | Replace (title required) |
| PATCH | `/api/tasks/<id>` | Partial update |
| PATCH | `/api/tasks/<id>/complete` | Mark completed (records `completed_at`) |
| PATCH | `/api/tasks/<id>/pending` | Mark pending again |
| DELETE | `/api/tasks/<id>` | Delete → 204 |

**List query parameters:** `status` (pending/completed), `search` (title/description), `priority`, `category`, `due_before`, `due_after`, `sort` (`id`, `title`, `due_date`, `priority`, `created_at`, `status`; prefix `-` for descending; default `-created_at`), `page`, `per_page` (max 100).

### Status codes

`200` OK · `201` created · `204` deleted · `400` bad query parameter · `401` missing/invalid/expired token or bad login · `404` not found (also returned for other users' tasks) · `409` email already registered · `422` validation failed (field-level `details`) · `500` unexpected error

## Security notes

- Passwords are stored only as salted hashes (Werkzeug), never in plain text.
- Tokens are signed and expire after 24 hours.
- Login returns the same error for an unknown email and a wrong password.
- Every task query is scoped to the logged-in user; all SQL values are bound parameters and sort fields are whitelisted.
