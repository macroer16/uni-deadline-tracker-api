"""The most important property: nobody can see or change anyone else's data."""

from datetime import UTC, datetime, timedelta

from tests.conftest import signup


def test_users_only_see_their_own_deadlines(client):
    victor = signup(client, email="victor@example.com")
    sam = signup(client, email="sam@example.com")
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    vid = client.post("/deadlines", json={"title": "Victor's essay", "due_at": due}, headers=victor).json()["id"]

    assert client.get("/deadlines", headers=sam).json() == []
    assert client.get("/deadlines/upcoming", headers=sam).json() == []
    # 404, not 403: Sam can't even tell that deadline exists.
    assert client.get(f"/deadlines/{vid}", headers=sam).status_code == 404
    assert client.patch(f"/deadlines/{vid}", json={"title": "hacked"}, headers=sam).status_code == 404
    assert client.delete(f"/deadlines/{vid}", headers=sam).status_code == 404
    assert client.get(f"/deadlines/{vid}", headers=victor).json()["title"] == "Victor's essay"


def test_cannot_attach_a_deadline_to_someone_elses_module(client):
    victor = signup(client, email="victor@example.com")
    sam = signup(client, email="sam@example.com")
    mid = client.post("/modules", json={"code": "CS101", "name": "A"}, headers=victor).json()["id"]
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()

    r = client.post("/deadlines", json={"title": "x", "due_at": due, "module_id": mid}, headers=sam)
    assert r.status_code == 404
    own = client.post("/deadlines", json={"title": "x", "due_at": due}, headers=sam).json()["id"]
    assert client.patch(f"/deadlines/{own}", json={"module_id": mid}, headers=sam).status_code == 404


def test_users_cannot_touch_each_others_modules(client):
    victor = signup(client, email="victor@example.com")
    sam = signup(client, email="sam@example.com")
    mid = client.post("/modules", json={"code": "CS101", "name": "A"}, headers=victor).json()["id"]
    assert client.get("/modules", headers=sam).json() == []
    assert client.put(f"/modules/{mid}", json={"code": "X", "name": "Y"}, headers=sam).status_code == 404
    assert client.delete(f"/modules/{mid}", headers=sam).status_code == 404
