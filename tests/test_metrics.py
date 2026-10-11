def test_metrics_use_route_templates_not_real_paths(client, auth):
    r = client.post("/deadlines", json={"title": "x", "due_at": "2030-01-01T09:00:00Z"}, headers=auth)
    did = r.json()["id"]
    client.get(f"/deadlines/{did}", headers=auth)
    token_url = client.post("/me/calendar-link", headers=auth).json()["url"]
    client.get(token_url)

    body = client.get("/metrics").text
    assert 'route="/deadlines/{deadline_id}"' in body
    assert f'/deadlines/{did}"' not in body
    # The secret calendar token must never leak into metrics.
    assert token_url.rsplit("/", 1)[1].removesuffix(".ics") not in body
    assert 'route="/calendar/{token}.ics"' in body


def test_business_counters_move(client, auth):
    def value(name):
        for line in client.get("/metrics").text.splitlines():
            if line.startswith(name + " "):
                return float(line.split()[1])
        return 0.0

    before = value("deadline_deadlines_created_total")
    client.post("/deadlines", json={"title": "x", "due_at": "2030-01-01T09:00:00Z"}, headers=auth)
    assert value("deadline_deadlines_created_total") == before + 1

    fails = value("deadline_login_failures_total")
    client.post("/auth/login", data={"username": "victor@example.com", "password": "wrong password!"})
    assert value("deadline_login_failures_total") == fails + 1


def test_probes_are_not_counted(client):
    client.get("/health")
    assert 'route="/health"' not in client.get("/metrics").text
