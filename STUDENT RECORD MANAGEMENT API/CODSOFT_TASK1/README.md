# CODSOFT_TASK1 — Student Record Management API

A REST backend (Flask + SQLite) managing **Students**, **Courses** and **Enrollments**.

## Run

```bash
pip install -r requirements.txt
python run.py            # http://127.0.0.1:5000
python -m pytest         # run the test suite
```

The SQLite file `students.db` is created automatically (override with the `DATABASE` env var).

## Project structure

```
app/
  __init__.py        application factory, blueprints, JSON error handlers
  db.py              SQLite connection + relational schema
  validators.py      input validation for each resource
  utils.py           error helper + search/filter/sort/pagination
  routes/            students.py, courses.py, enrollments.py
tests/test_api.py    pytest suite
run.py               entry point
```

## Data model

- **students** — id, first_name, last_name, email (unique), phone, date_of_birth, created_at
- **courses** — id, code (unique), title, description, credits (1-10), created_at
- **enrollments** — id, student_id → students, course_id → courses, status (enrolled/completed/dropped), grade (A-F), enrolled_on; unique (student_id, course_id); cascades on delete

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET/POST | `/api/students` | List / create |
| GET/PUT/PATCH/DELETE | `/api/students/<id>` | Retrieve (with courses) / replace / partial update / delete |
| GET/POST | `/api/courses` | List / create |
| GET/PUT/PATCH/DELETE | `/api/courses/<id>` | Retrieve (with students) / replace / partial update / delete |
| GET/POST | `/api/enrollments` | List / enroll a student in a course |
| GET/PATCH/DELETE | `/api/enrollments/<id>` | Retrieve / update status & grade / remove |

### List query parameters (all list endpoints)

- `search=` — substring match (students: name/email, courses: code/title/description, enrollments: student/course)
- Filters — students: `last_name`, `email`; courses: `credits`, `code`; enrollments: `student_id`, `course_id`, `status`, `grade`
- `sort=field` or `sort=-field` (descending); invalid fields return 400
- `page` (default 1), `per_page` (default 10, max 100)

Response shape: `{"data": [...], "pagination": {"page", "per_page", "total", "pages"}}`

### Status codes

`200` OK · `201` created · `204` deleted · `400` bad query/empty update · `404` not found · `409` duplicate (email, course code, enrollment) · `422` validation failed (field-level `details`) · `500` unexpected error

### Example

```bash
curl -X POST localhost:5000/api/students -H 'Content-Type: application/json' \
  -d '{"first_name":"Asha","last_name":"Verma","email":"asha@example.com"}'

curl -X POST localhost:5000/api/courses -H 'Content-Type: application/json' \
  -d '{"code":"CS101","title":"Intro to Programming","credits":4}'

curl -X POST localhost:5000/api/enrollments -H 'Content-Type: application/json' \
  -d '{"student_id":1,"course_id":1}'

curl 'localhost:5000/api/students?search=asha&sort=-id&page=1&per_page=5'
```
