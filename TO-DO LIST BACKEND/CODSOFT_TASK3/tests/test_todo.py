import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"DATABASE": str(tmp_path / "t.db"), "TESTING": True,
                       "SECRET_KEY": "test-key"})


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="a@example.com", password="password123"):
    r = client.post("/api/auth/register", json={"name": "Asha", "email": email,
                                                "password": password})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


@pytest.fixture
def auth(client):
    return register(client)


def add(client, auth, title="Task", **over):
    return client.post("/api/tasks", json={"title": title, **over}, headers=auth)


# ---- authentication ----
def test_register_login_me(client):
    h = register(client)
    assert client.get("/api/auth/me", headers=h).get_json()["email"] == "a@example.com"
    r = client.post("/api/auth/login", json={"email": "A@Example.com", "password": "password123"})
    assert r.status_code == 200 and "token" in r.get_json()
    assert "password" not in str(client.get("/api/auth/me", headers=h).get_json())


def test_register_errors(client):
    register(client)
    r = client.post("/api/auth/register", json={"name": "B", "email": "a@example.com",
                                                "password": "password123"})
    assert r.status_code == 409
    r = client.post("/api/auth/register", json={"name": "", "email": "bad", "password": "short"})
    assert r.status_code == 422 and {"name", "email", "password"} <= set(r.get_json()["details"])


def test_login_failures_are_generic(client):
    register(client)
    wrong_pw = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope12345"})
    no_user = client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope12345"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.get_json() == no_user.get_json()


def test_password_is_hashed(client, app):
    register(client)
    import sqlite3
    row = sqlite3.connect(app.config["DATABASE"]).execute("SELECT password_hash FROM users").fetchone()
    assert "password123" not in row[0] and row[0].count("$") >= 2


def test_tasks_require_token(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/tasks", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert client.post("/api/tasks", json={"title": "x"}).status_code == 401


def test_expired_token(app, client):
    h = register(client)
    app.config["TOKEN_MAX_AGE"] = -1
    assert client.get("/api/tasks", headers=h).status_code == 401


# ---- tasks ----
def test_task_crud(client, auth):
    r = add(client, auth, "Buy milk", description="2 litres", priority="high",
            category="Home", due_date="2030-01-31")
    assert r.status_code == 201
    t = r.get_json()
    assert t["status"] == "pending" and t["priority"] == "high"
    tid = t["id"]
    assert client.get(f"/api/tasks/{tid}", headers=auth).status_code == 200
    r = client.patch(f"/api/tasks/{tid}", json={"title": "Buy oat milk"}, headers=auth)
    assert r.get_json()["title"] == "Buy oat milk"
    assert client.put(f"/api/tasks/{tid}", json={"priority": "low"}, headers=auth).status_code == 422
    assert client.delete(f"/api/tasks/{tid}", headers=auth).status_code == 204
    assert client.get(f"/api/tasks/{tid}", headers=auth).status_code == 404


def test_task_validation(client, auth):
    r = add(client, auth, "", priority="urgent", due_date="31-01-2030", status="done")
    assert r.status_code == 422
    assert {"title", "priority", "due_date", "status"} <= set(r.get_json()["details"])
    assert client.post("/api/tasks", data="{bad", content_type="application/json",
                       headers=auth).status_code == 422
    assert client.patch("/api/tasks/1", json={"title": "x"}, headers=auth).status_code == 404


def test_complete_and_pending(client, auth):
    tid = add(client, auth).get_json()["id"]
    r = client.patch(f"/api/tasks/{tid}/complete", headers=auth).get_json()
    assert r["status"] == "completed" and r["completed_at"]
    r = client.patch(f"/api/tasks/{tid}/pending", headers=auth).get_json()
    assert r["status"] == "pending" and r["completed_at"] is None
    r = client.patch(f"/api/tasks/{tid}", json={"status": "completed"}, headers=auth).get_json()
    assert r["completed_at"]


def test_filter_search_sort_paginate(client, auth):
    add(client, auth, "Write report", priority="high", category="Work", due_date="2030-03-01")
    add(client, auth, "Buy groceries", priority="low", category="Home", due_date="2030-01-01")
    done = add(client, auth, "Pay rent", priority="medium", category="Home",
               due_date="2030-02-01").get_json()["id"]
    client.patch(f"/api/tasks/{done}/complete", headers=auth)
    q = lambda s: client.get(f"/api/tasks?{s}", headers=auth).get_json()

    assert q("status=completed")["pagination"]["total"] == 1
    assert q("status=pending")["pagination"]["total"] == 2
    assert q("search=report")["data"][0]["title"] == "Write report"
    assert q("category=home")["pagination"]["total"] == 2
    assert q("priority=high")["pagination"]["total"] == 1
    assert q("due_before=2030-02-01")["pagination"]["total"] == 2
    assert [t["title"] for t in q("sort=-priority")["data"]] == \
        ["Write report", "Pay rent", "Buy groceries"]
    assert [t["title"] for t in q("sort=due_date")["data"]][0] == "Buy groceries"
    p = q("per_page=2&page=2&sort=id")
    assert len(p["data"]) == 1 and p["pagination"]["pages"] == 2
    for bad in ("status=done", "sort=password", "page=0", "due_before=tomorrow"):
        assert client.get(f"/api/tasks?{bad}", headers=auth).status_code == 400


def test_users_cannot_access_each_others_tasks(client, auth):
    other = register(client, "b@example.com")
    tid = add(client, auth, "Private").get_json()["id"]
    assert client.get(f"/api/tasks/{tid}", headers=other).status_code == 404
    assert client.patch(f"/api/tasks/{tid}", json={"title": "hacked"}, headers=other).status_code == 404
    assert client.patch(f"/api/tasks/{tid}/complete", headers=other).status_code == 404
    assert client.delete(f"/api/tasks/{tid}", headers=other).status_code == 404
    assert client.get("/api/tasks", headers=other).get_json()["pagination"]["total"] == 0
    assert client.get(f"/api/tasks/{tid}", headers=auth).get_json()["title"] == "Private"


def test_sql_injection_is_inert(client, auth):
    add(client, auth)
    r = client.get("/api/tasks?search=' OR 1=1 --", headers=auth)
    assert r.status_code == 200 and r.get_json()["pagination"]["total"] == 0


def test_unknown_route_json_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "error" in r.get_json()
