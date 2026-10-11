from datetime import UTC, datetime, timedelta

from app.ics import _escape, _fold


def test_calendar_feed_end_to_end(client, auth):
    client.post("/modules", json={"code": "CS101", "name": "Programming"}, headers=auth)
    mid = client.get("/modules", headers=auth).json()[0]["id"]
    due = datetime(2026, 12, 4, 16, 0, tzinfo=UTC).isoformat()
    client.post(
        "/deadlines", json={"title": "Coursework 1, part A", "due_at": due, "module_id": mid, "weight_percent": 50}, headers=auth
    )

    url = client.post("/me/calendar-link", headers=auth).json()["url"]
    r = client.get(url)  # no auth header: the secret link is the authentication
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert body.startswith("BEGIN:VCALENDAR\r\n") and body.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:CS101: Coursework 1\\, part A" in body
    assert "DTEND:20261204T160000Z" in body
    assert "DTSTART:20261204T153000Z" in body
    assert "TRIGGER:-P1D" in body
    assert "Worth 50% of the module" in body


def test_rotating_the_link_breaks_the_old_one(client, auth):
    old = client.post("/me/calendar-link", headers=auth).json()["url"]
    new = client.post("/me/calendar-link", headers=auth).json()["url"]
    assert old != new
    assert client.get(old).status_code == 404
    assert client.get(new).status_code == 200


def test_unknown_link_is_404(client):
    assert client.get("/calendar/not-a-real-token.ics").status_code == 404


def test_submitted_deadlines_have_no_reminder(client, auth):
    due = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    client.post("/deadlines", json={"title": "Done one", "due_at": due, "status": "submitted"}, headers=auth)
    body = client.get(client.post("/me/calendar-link", headers=auth).json()["url"]).text
    assert "SUMMARY:✓ Done one" in body
    assert "VALARM" not in body


def test_escaping_and_line_folding():
    assert _escape("a,b;c\\d\ne") == "a\\,b\;c\\\\d\\ne"
    folded = _fold("SUMMARY:" + "é" * 60)  # é is 2 bytes in UTF-8
    lines = folded.split("\r\n")
    assert all(len(line.encode()) <= 75 for line in lines)
    assert all(line.startswith(" ") for line in lines[1:])
    assert "".join(line[1:] if i else line for i, line in enumerate(lines)) == "SUMMARY:" + "é" * 60
