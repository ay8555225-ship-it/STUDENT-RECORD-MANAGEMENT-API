import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


def add(client, n=1, **over):
    body = {"name": f"Person {n}", "email": f"p{n}@example.com",
            "phone": f"+91 98765 {10000 + n}", **over}
    return client.post("/api/contacts", json=body)


def test_crud_cycle(client):
    r = add(client, address="Varanasi", company="Acme")
    assert r.status_code == 201
    c = r.get_json()
    assert c["phone"] == "+919876510001"  # normalised
    cid = c["id"]
    assert client.get(f"/api/contacts/{cid}").get_json()["company"] == "Acme"
    r = client.patch(f"/api/contacts/{cid}", json={"company": "Globex"})
    assert r.get_json()["company"] == "Globex"
    r = client.put(f"/api/contacts/{cid}", json={"name": "Only Name"})
    assert r.status_code == 422
    assert client.delete(f"/api/contacts/{cid}").status_code == 204
    assert client.get(f"/api/contacts/{cid}").status_code == 404
    assert client.delete(f"/api/contacts/{cid}").status_code == 404


def test_validation(client):
    r = client.post("/api/contacts", json={"name": " ", "email": "nope", "phone": "abc"})
    assert r.status_code == 422
    assert {"name", "email", "phone"} <= set(r.get_json()["details"])
    assert client.post("/api/contacts", data="{bad", content_type="application/json").status_code == 422
    assert client.patch("/api/contacts/1", json={}).status_code == 404


def test_duplicates_blocked(client):
    assert add(client).status_code == 201
    # same email, different case
    assert add(client, 2, email="P1@Example.com").status_code == 409
    # same phone, different formatting
    assert add(client, 3, phone="+91-98765-10001").status_code == 409
    # update colliding with another contact
    other = add(client, 4).get_json()["id"]
    r = client.patch(f"/api/contacts/{other}", json={"email": "p1@example.com"})
    assert r.status_code == 409
    # updating a contact to its own values is fine
    r = client.patch(f"/api/contacts/{other}", json={"email": "p4@example.com"})
    assert r.status_code == 200


def test_search(client):
    add(client, 1, name="Asha Verma", company="Acme")
    add(client, 2, name="Ravi Kumar", company="Globex")
    add(client, 3, name="Asha Singh", company="Globex")
    q = lambda s: client.get(f"/api/contacts?{s}").get_json()
    assert q("search=asha")["pagination"]["total"] == 2
    assert q("search=p2@example")["pagination"]["total"] == 1
    assert q("search=98765 10002")["pagination"]["total"] == 1   # formatted phone
    assert q("search=%2B9198765")["pagination"]["total"] == 3
    assert q("company=globex")["pagination"]["total"] == 2


def test_sort_and_pagination(client):
    for i in range(1, 8):
        add(client, i, name=f"Name{i}")
    r = client.get("/api/contacts?sort=-name&per_page=3&page=2").get_json()
    assert [c["name"] for c in r["data"]] == ["Name4", "Name3", "Name2"]
    assert r["pagination"] == {"page": 2, "per_page": 3, "total": 7, "pages": 3}
    assert client.get("/api/contacts?sort=phone;drop").status_code == 400
    assert client.get("/api/contacts?per_page=1000").status_code == 400
    assert client.get("/api/contacts?page=abc").status_code == 400


def test_sql_injection_is_inert(client):
    add(client)
    r = client.get("/api/contacts?search=' OR 1=1 --")
    assert r.status_code == 200 and r.get_json()["pagination"]["total"] == 0


def test_unknown_route_json_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "error" in r.get_json()
