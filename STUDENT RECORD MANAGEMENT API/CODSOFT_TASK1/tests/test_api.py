import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


def make_student(client, n=1, **over):
    body = {"first_name": f"Stu{n}", "last_name": f"Last{n}",
            "email": f"s{n}@example.com", **over}
    return client.post("/api/students", json=body)


def make_course(client, code="CS101", **over):
    return client.post("/api/courses", json={"code": code, "title": f"Course {code}", **over})


# ---- students ----
def test_student_crud(client):
    r = make_student(client, phone="+91 98765 43210", date_of_birth="2003-05-10")
    assert r.status_code == 201
    sid = r.get_json()["id"]
    assert client.get(f"/api/students/{sid}").status_code == 200
    r = client.patch(f"/api/students/{sid}", json={"last_name": "Sharma"})
    assert r.get_json()["last_name"] == "Sharma"
    r = client.put(f"/api/students/{sid}", json={"first_name": "A"})
    assert r.status_code == 422  # PUT requires full body
    assert client.delete(f"/api/students/{sid}").status_code == 204
    assert client.get(f"/api/students/{sid}").status_code == 404


def test_student_validation(client):
    r = client.post("/api/students", json={"first_name": "", "email": "bad"})
    assert r.status_code == 422
    assert {"first_name", "last_name", "email"} <= set(r.get_json()["details"])
    r = make_student(client, date_of_birth="2999-01-01")
    assert r.status_code == 422
    assert client.post("/api/students", data="notjson",
                       content_type="application/json").status_code == 422


def test_duplicate_email(client):
    assert make_student(client).status_code == 201
    assert make_student(client).status_code == 409


def test_search_sort_paginate(client):
    for i in range(1, 8):
        make_student(client, i)
    r = client.get("/api/students?per_page=3&page=3&sort=-id").get_json()
    assert r["pagination"] == {"page": 3, "per_page": 3, "total": 7, "pages": 3}
    assert [s["id"] for s in r["data"]] == [1]
    r = client.get("/api/students?search=Stu5").get_json()
    assert r["pagination"]["total"] == 1
    assert client.get("/api/students?sort=password").status_code == 400
    assert client.get("/api/students?page=0").status_code == 400


# ---- courses ----
def test_course_crud_and_validation(client):
    r = make_course(client, code="cs101", credits=4)
    assert r.status_code == 201 and r.get_json()["code"] == "CS101"
    assert make_course(client, code="CS101").status_code == 409
    assert make_course(client, code="!!").status_code == 422
    assert make_course(client, code="MA101", credits=99).status_code == 422
    cid = r.get_json()["id"]
    assert client.patch(f"/api/courses/{cid}", json={"title": "New"}).status_code == 200
    assert client.get("/api/courses?credits=4").get_json()["pagination"]["total"] == 1
    assert client.delete(f"/api/courses/{cid}").status_code == 204


# ---- enrollments ----
def test_enrollment_flow(client):
    sid = make_student(client).get_json()["id"]
    cid = make_course(client).get_json()["id"]
    r = client.post("/api/enrollments", json={"student_id": sid, "course_id": cid})
    assert r.status_code == 201
    eid = r.get_json()["id"]
    assert client.post("/api/enrollments",
                       json={"student_id": sid, "course_id": cid}).status_code == 409
    assert client.post("/api/enrollments",
                       json={"student_id": 999, "course_id": cid}).status_code == 404
    r = client.patch(f"/api/enrollments/{eid}", json={"status": "completed", "grade": "a"})
    assert r.get_json()["grade"] == "A"
    assert client.patch(f"/api/enrollments/{eid}", json={"grade": "Z"}).status_code == 422
    assert len(client.get(f"/api/students/{sid}").get_json()["courses"]) == 1
    assert client.get(f"/api/enrollments?student_id={sid}").get_json()["pagination"]["total"] == 1
    # cascade: deleting the student removes enrollments
    client.delete(f"/api/students/{sid}")
    assert client.get(f"/api/enrollments/{eid}").status_code == 404


def test_unknown_route_returns_json_404(client):
    r = client.get("/api/nothing")
    assert r.status_code == 404 and "error" in r.get_json()
