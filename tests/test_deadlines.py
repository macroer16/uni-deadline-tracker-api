from datetime import UTC, datetime, timedelta

from tests.conftest import signup


def iso(dt):
    return dt.isoformat()


def soon(**kw):
    return iso(datetime.now(UTC) + timedelta(**kw))


def make(client, auth, **fields):
    body = {"title": "Essay", "due_at": soon(days=10)} | fields
    r = client.post("/deadlines", json=body, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_read_back(client, auth):
    d = make(client, auth, title="Lab report", weight_percent=40, notes="Use the template")
    got = client.get(f"/deadlines/{d['id']}", headers=auth).json()
    assert got["title"] == "Lab report"
    assert got["weight_percent"] == 40
    assert got["status"] == "todo"
    assert got["urgency"] == "later"


def test_due_date_without_timezone_is_rejected(client, auth):
    r = client.post("/deadlines", json={"title": "x", "due_at": "2026-11-01T12:00:00"}, headers=auth)
    assert r.status_code == 422


def test_times_are_stored_and_returned_in_utc(client, auth):
    d = make(client, auth, due_at="2026-11-01T12:00:00+01:00")
    assert d["due_at"].startswith("2026-11-01T11:00:00")
    assert d["due_at"].endswith(("Z", "+00:00"))


def test_validation(client, auth):
    assert client.post("/deadlines", json={"title": "", "due_at": soon(days=1)}, headers=auth).status_code == 422
    assert (
        client.post("/deadlines", json={"title": "x", "due_at": soon(days=1), "weight_percent": 101}, headers=auth).status_code
        == 422
    )
    assert (
        client.post("/deadlines", json={"title": "x", "due_at": soon(days=1), "status": "lost"}, headers=auth).status_code == 422
    )


def test_list_is_sorted_by_due_date(client, auth):
    make(client, auth, title="Later", due_at=soon(days=20))
    make(client, auth, title="Sooner", due_at=soon(days=2))
    titles = [d["title"] for d in client.get("/deadlines", headers=auth).json()]
    assert titles == ["Sooner", "Later"]


def test_filters(client, auth):
    make(client, auth, title="A", status="submitted")
    make(client, auth, title="B")
    assert [d["title"] for d in client.get("/deadlines?status=submitted", headers=auth).json()] == ["A"]
    assert [d["title"] for d in client.get("/deadlines?include_submitted=false", headers=auth).json()] == ["B"]


def test_upcoming_shows_overdue_and_soon_but_not_far_or_submitted(client, auth):
    make(client, auth, title="Overdue", due_at=soon(days=-1))
    make(client, auth, title="Tomorrow", due_at=soon(hours=20))
    make(client, auth, title="Next week", due_at=soon(days=5))
    make(client, auth, title="Far away", due_at=soon(days=60))
    make(client, auth, title="Done", due_at=soon(days=1), status="submitted")
    got = client.get("/deadlines/upcoming?days=7", headers=auth).json()
    assert [(d["title"], d["urgency"]) for d in got] == [
        ("Overdue", "overdue"),
        ("Tomorrow", "due_soon"),
        ("Next week", "this_week"),
    ]


def test_patch_changes_only_what_is_sent(client, auth):
    d = make(client, auth, title="Essay", weight_percent=30)
    r = client.patch(f"/deadlines/{d['id']}", json={"status": "submitted"}, headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"
    assert r.json()["urgency"] == "done"
    assert r.json()["weight_percent"] == 30


def test_patch_cannot_blank_required_fields(client, auth):
    d = make(client, auth)
    assert client.patch(f"/deadlines/{d['id']}", json={"title": None}, headers=auth).status_code == 422
    assert client.patch(f"/deadlines/{d['id']}", json={"due_at": None}, headers=auth).status_code == 422


def test_delete(client, auth):
    d = make(client, auth)
    assert client.delete(f"/deadlines/{d['id']}", headers=auth).status_code == 204
    assert client.get(f"/deadlines/{d['id']}", headers=auth).status_code == 404


def test_modules_link_to_deadlines(client, auth):
    m = client.post("/modules", json={"code": "cs101", "name": "Programming"}, headers=auth).json()
    assert m["code"] == "CS101"
    d = make(client, auth, module_id=m["id"])
    assert d["module_code"] == "CS101"
    assert [x["title"] for x in client.get(f"/deadlines?module_id={m['id']}", headers=auth).json()] == ["Essay"]


def test_deleting_a_module_keeps_its_deadlines(client, auth):
    m = client.post("/modules", json={"code": "CS101", "name": "Programming"}, headers=auth).json()
    d = make(client, auth, module_id=m["id"])
    assert client.delete(f"/modules/{m['id']}", headers=auth).status_code == 204
    got = client.get(f"/deadlines/{d['id']}", headers=auth).json()
    assert got["module_id"] is None and got["module_code"] is None


def test_duplicate_module_code_rejected_per_user_only(client, auth):
    assert client.post("/modules", json={"code": "CS101", "name": "A"}, headers=auth).status_code == 201
    assert client.post("/modules", json={"code": "cs101", "name": "B"}, headers=auth).status_code == 409
    other = signup(client, email="sam@example.com")
    assert client.post("/modules", json={"code": "CS101", "name": "A"}, headers=other).status_code == 201


def test_deleting_account_deletes_everything(client, auth):
    make(client, auth)
    client.post("/modules", json={"code": "CS101", "name": "A"}, headers=auth)
    assert client.delete("/me", headers=auth).status_code == 204
    # Signing up again with the same email starts empty.
    again = signup(client)
    assert client.get("/deadlines", headers=again).json() == []
    assert client.get("/modules", headers=again).json() == []


def test_health_checks(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/live").json() == {"status": "ok"}
