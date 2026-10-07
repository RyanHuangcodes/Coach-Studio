import uuid

from fastapi.testclient import TestClient

from app.main import app


def _email(prefix="u"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


def signup_coach():
    c = TestClient(app)
    assert c.post(
        "/api/auth/signup",
        json={"email": _email("coach"), "password": "password123", "display_name": "Coach"},
    ).status_code == 201
    return c


def make_player(coach, name="Player"):
    rid = coach.get("/api/rosters").json()[0]["id"]
    pid = coach.post("/api/players", json={"name": name, "roster_id": rid}).json()["id"]
    email = _email("player")
    assert coach.post(
        f"/api/players/{pid}/account", json={"email": email, "password": "playerpass1"}
    ).status_code == 200
    pc = TestClient(app)
    assert pc.post("/api/auth/login", json={"email": email, "password": "playerpass1"}).status_code == 200
    return pid, pc


def test_player_role_boundaries():
    coach = signup_coach()
    pid, pc = make_player(coach)
    assert pc.get("/api/auth/me").json()["role"] == "player"
    assert pc.get("/api/rosters").status_code == 403
    assert pc.post(f"/api/players/{pid}/assignments", json={"category": "skills", "title": "x"}).status_code == 403
    assert coach.get("/api/me/assignments").status_code == 403


def test_messaging_and_unread():
    coach = signup_coach()
    pid, pc = make_player(coach)
    coach.post(f"/api/players/{pid}/messages", json={"body": "Welcome"})
    assert pc.get("/api/me/unread").json()["count"] == 1
    assert [m["body"] for m in pc.get("/api/me/messages").json()] == ["Welcome"]
    pc.post("/api/me/messages", json={"body": "Thanks"})
    assert coach.get("/api/comms/unread").json()["total"] == 1
    coach.post(f"/api/players/{pid}/messages/read")
    assert coach.get("/api/comms/unread").json()["total"] == 0


def test_assignments_categories_and_due():
    coach = signup_coach()
    pid, pc = make_player(coach)
    for cat in ("skills", "strength", "recovery"):
        coach.post(f"/api/players/{pid}/assignments", json={"category": cat, "title": f"{cat} task"})
    coach.post(f"/api/players/{pid}/assignments", json={"category": "strength", "title": "squats", "due_date": "2026-10-20"})
    items = pc.get("/api/me/assignments").json()
    assert {i["category"] for i in items} == {"skills", "strength", "recovery"}
    assert any(i["due_date"] == "2026-10-20" for i in items)
    aid = items[0]["id"]
    assert pc.patch(f"/api/me/assignments/{aid}", json={"done": True}).json()["done"] is True


def test_bad_assignment_category_rejected():
    coach = signup_coach()
    pid, _ = make_player(coach)
    assert coach.post(f"/api/players/{pid}/assignments", json={"category": "cardio", "title": "x"}).status_code == 422


def test_feedback_flow():
    coach = signup_coach()
    pid, pc = make_player(coach)
    coach.post(f"/api/players/{pid}/feedback", json={"session_label": "Tue", "body": "Nice work"})
    fb = pc.get("/api/me/feedback").json()
    assert len(fb) == 1 and fb[0]["body"] == "Nice work"
    assert pc.post(f"/api/players/{pid}/feedback", json={"body": "x"}).status_code == 403


def test_training_access_gate():
    coach = signup_coach()
    pid, pc = make_player(coach)
    assert pc.get("/api/me/trainings").status_code == 403
    coach.patch(f"/api/players/{pid}/training-access", json={"can_view_trainings": True})
    coach.post("/api/plans", json={"sport": "Badminton", "duration_minutes": 60, "name": "Footwork"})
    tr = pc.get("/api/me/trainings")
    assert tr.status_code == 200 and len(tr.json()) == 1
