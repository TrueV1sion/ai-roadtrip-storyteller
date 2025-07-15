from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime

from backend.app.routes.experience import trivia, games, reservations, pitstops, interactive
from backend.app.routes.itinerary import router as itinerary_router

app = FastAPI()

# Include Experience routers under /experience and itinerary router
app.include_router(trivia.router, prefix="/experience")
app.include_router(games.router, prefix="/experience")
app.include_router(reservations.router, prefix="/experience")
app.include_router(pitstops.router, prefix="/experience")
app.include_router(interactive.router, prefix="/experience")
app.include_router(itinerary_router)

client = TestClient(app)

def test_get_trivia():
    response = client.get("/experience/trivia")
    assert response.status_code == 200
    data = response.json()
    assert "question" in data


def test_answer_trivia_correct():
    payload = {
        "question": "What is the tallest mountain in the world?",
        "answer": "Mount Everest"
    }
    response = client.post("/experience/trivia/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("correct") is True


def test_answer_trivia_incorrect():
    payload = {
        "question": "What is the tallest mountain in the world?",
        "answer": "K2"
    }
    response = client.post("/experience/trivia/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("correct") is False


def test_get_game():
    response = client.get("/experience/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data and "prompt" in data


def test_answer_game():
    payload = {"name": "Guess the Landmark", "answer": "Eiffel Tower"}
    response = client.post("/experience/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("correct") is True


def test_reservations_crud():
    now_iso = datetime.now().isoformat()
    payload = {"name": "Test Reservation", "location": "Hotel California", "datetime": now_iso}
    response = client.post("/experience/reservations", json=payload)
    assert response.status_code == 200
    reservation = response.json()
    reservation_id = reservation.get("id")
    assert reservation_id is not None

    response = client.get(f"/experience/reservations/{reservation_id}")
    assert response.status_code == 200
    reservation_get = response.json()
    assert reservation_get["name"] == "Test Reservation"

    update_payload = {"name": "Updated Reservation"}
    response = client.put(f"/experience/reservations/{reservation_id}", json=update_payload)
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Updated Reservation"

    response = client.delete(f"/experience/reservations/{reservation_id}")
    assert response.status_code == 200
    deletion = response.json()
    assert "Reservation deleted successfully" in deletion.get("detail", "")


def test_pitstops_crud():
    payload = {"name": "Scenic Rest Stop", "location": "Countryside", "type": "rest"}
    response = client.post("/experience/pitstops", json=payload)
    assert response.status_code == 200
    pitstop = response.json()
    pitstop_id = pitstop.get("id")
    assert pitstop_id is not None

    response = client.get(f"/experience/pitstops/{pitstop_id}")
    assert response.status_code == 200
    pitstop_get = response.json()
    assert pitstop_get["name"] == "Scenic Rest Stop"

    update_payload = {"name": "Updated Rest Stop"}
    response = client.put(f"/experience/pitstops/{pitstop_id}", json=update_payload)
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Updated Rest Stop"

    response = client.delete(f"/experience/pitstops/{pitstop_id}")
    assert response.status_code == 200
    deletion = response.json()
    assert "Pit stop deleted successfully" in deletion.get("detail", "")


def test_get_itinerary():
    now_iso = datetime.now().isoformat()
    reservation_payload = {"name": "Itinerary Reservation", "location": "Test Location", "datetime": now_iso}
    client.post("/experience/reservations", json=reservation_payload)
    
    pitstop_payload = {"name": "Itinerary Pit Stop", "location": "Test Town", "type": "food"}
    client.post("/experience/pitstops", json=pitstop_payload)
    
    response = client.get("/itinerary")
    assert response.status_code == 200
    itinerary = response.json()
    assert "reservations" in itinerary and "pitstops" in itinerary
    assert len(itinerary["reservations"]) > 0
    assert len(itinerary["pitstops"]) > 0


def test_interactive_sessions():
    now_iso = datetime.now().isoformat()
    payload = {"type": "trivia", "scheduled_time": now_iso, "description": "Test session"}
    response = client.post("/experience/interactive", json=payload)
    assert response.status_code == 200
    session_obj = response.json()
    session_id = session_obj.get("id")
    assert session_id is not None

    response = client.get("/experience/interactive")
    assert response.status_code == 200
    data = response.json()
    sessions = data.get("interactive_sessions", [])
    assert any(s.get("id") == session_id for s in sessions)

    response = client.delete(f"/experience/interactive/{session_id}")
    assert response.status_code == 200
    deletion = response.json()
    assert "Interactive session deleted successfully" in deletion.get("detail", "") 