import uuid

from fastapi.testclient import TestClient

from app.main import app


def _email(prefix="u"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def signup(name="Coach"):
    c = TestClient(app)
    r = c.post(
        "/api/auth/signup",
        json={"email": _email("coach"), "password": "password123", "display_name": name},
    )
    assert r.status_code == 201, r.text
    return c


def test_signup_sets_role_and_defaults():
    c = signup()
    me = c.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "coach"
    rosters = c.get("/api/rosters").json()
    assert len(rosters) == 1 and rosters[0]["name"] == "All Players"
    assert len(c.get("/api/tiers").json()) >= 1


def test_login_wrong_password_401():
    email = _email("coach")
    TestClient(app).post(
        "/api/auth/signup", json={"email": email, "password": "password123", "display_name": "C"}
    )
    bad = TestClient(app).post("/api/auth/login", json={"email": email, "password": "nope12345"})
    assert bad.status_code == 401


def test_endpoints_require_auth():
    assert TestClient(app).get("/api/rosters").status_code == 401
    assert TestClient(app).get("/api/players").status_code == 401


def test_roster_isolation_between_coaches():
    a = signup()
    b = signup()
    rid = a.get("/api/rosters").json()[0]["id"]
    pid = a.post("/api/players", json={"name": "Alice", "roster_id": rid}).json()["id"]
    # B sees none of A's data and cannot act on A's player
    assert b.get("/api/players").json() == []
    assert b.post(f"/api/players/{pid}/account", json={"email": _email("p"), "password": "password123"}).status_code == 404
    assert b.patch(f"/api/players/{pid}/training-access", json={"can_view_trainings": True}).status_code == 404


def test_attendance_per_lesson_and_calendar():
    coach = signup()
    rid = coach.get("/api/rosters").json()[0]["id"]
    pid = coach.post("/api/players", json={"name": "Al", "roster_id": rid}).json()["id"]
    pr = coach.post("/api/practices/for-date", json={"roster_id": rid, "date": "2026-10-01"}).json()
    coach.post(f"/api/practices/{pr['id']}/attendance", json={"player_id": pid})
    bd = coach.get(f"/api/practices/by-date?roster_id={rid}&date=2026-10-01").json()
    assert bd["practice_id"] == pr["id"] and pid in bd["player_ids"]
    cal = coach.get(f"/api/practices/calendar?roster_id={rid}").json()
    assert any(d["date"] == "2026-10-01" and d["attendee_count"] == 1 for d in cal)


def test_health():
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}
