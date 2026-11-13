import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# Isolated in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =====================================================================
# Endpoint 1: POST /centers (create_center)
# =====================================================================

def test_create_center_success(client):
    payload = {"name": "Brightpath Learning Center", "city": "Nagpur"}
    response = client.post("/centers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == payload["name"]
    assert data["city"] == payload["city"]
    assert "sessions" not in data


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"name": "", "city": "Nagpur"},              # Empty name
        {"name": "Brightpath", "city": ""},          # Empty city
        {"name": "Brightpath"},                       # Missing city
        {"city": "Nagpur"},                           # Missing name
        {"name": 12345, "city": "Nagpur"},           # Wrong type for name
        {"name": "Brightpath", "city": 67890},        # Wrong type for city
    ],
)
def test_create_center_validation_errors(client, invalid_payload):
    response = client.post("/centers", json=invalid_payload)
    assert response.status_code == 422


# =====================================================================
# Endpoint 2: POST /centers/{center_id}/sessions (add_session)
# =====================================================================

def test_add_session_success(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    session_payload = {
        "student_name": "Aisha Khan",
        "status": "confirmed",
        "duration": 45,
    }
    response = client.post(f"/centers/{center_id}/sessions", json=session_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["student_name"] == "Aisha Khan"
    assert data["status"] == "confirmed"
    assert data["duration"] == 45


def test_add_session_duration_boundary(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    # Inclusive minimum of 15 must succeed
    valid_payload = {
        "student_name": "Rohan Gupta",
        "status": "pending",
        "duration": 15,
    }
    response = client.post(f"/centers/{center_id}/sessions", json=valid_payload)
    assert response.status_code == 201

    # Duration below 15 must fail
    invalid_payload = {
        "student_name": "Rohan Gupta",
        "status": "pending",
        "duration": 14,
    }
    bad_response = client.post(f"/centers/{center_id}/sessions", json=invalid_payload)
    assert bad_response.status_code == 422


def test_add_session_center_not_found(client):
    payload = {"student_name": "Aisha Khan", "status": "confirmed", "duration": 45}
    response = client.post("/centers/999/sessions", json=payload)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"student_name": "", "status": "confirmed", "duration": 45},  # Empty student_name
        {"student_name": "Aisha", "status": "", "duration": 45},       # Empty status
        {"student_name": "Aisha", "status": "confirmed"},              # Missing duration
        {"status": "confirmed", "duration": 45},                       # Missing student_name
        {"student_name": "Aisha", "duration": 45},                     # Missing status
        {"student_name": "Aisha", "status": "confirmed", "duration": "forty-five"},  # Wrong type
    ],
)
def test_add_session_validation_errors(client, invalid_payload):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    response = client.post(f"/centers/{center_id}/sessions", json=invalid_payload)
    assert response.status_code == 422


# =====================================================================
# Endpoint 3: GET /centers/{center_id} (get_center)
# =====================================================================

def test_get_center_with_all_sessions(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Zara", "status": "pending", "duration": 30},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 60},
    )

    response = client.get(f"/centers/{center_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == center_id
    assert data["name"] == "Brightpath"
    assert data["city"] == "Nagpur"
    assert len(data["sessions"]) == 2


def test_get_center_filtered_by_status(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Zara", "status": "pending", "duration": 30},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 60},
    )

    response = client.get(f"/centers/{center_id}?status=confirmed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["student_name"] == "Aisha"
    assert data["sessions"][0]["status"] == "confirmed"


def test_get_center_sorted_by_duration(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Zara", "status": "confirmed", "duration": 60},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 20},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Kabir", "status": "confirmed", "duration": 45},
    )

    response = client.get(f"/centers/{center_id}?sort=duration")
    assert response.status_code == 200
    durations = [s["duration"] for s in response.json()["sessions"]]
    assert durations == [20, 45, 60]


def test_get_center_sorted_by_student_name(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Zara", "status": "confirmed", "duration": 30},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 45},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Kabir", "status": "confirmed", "duration": 60},
    )

    response = client.get(f"/centers/{center_id}?sort=student_name")
    assert response.status_code == 200
    names = [s["student_name"] for s in response.json()["sessions"]]
    assert names == ["Aisha", "Kabir", "Zara"]


def test_get_center_filtered_and_sorted(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Zara", "status": "confirmed", "duration": 60},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Kabir", "status": "pending", "duration": 15},
    )
    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 30},
    )

    response = client.get(f"/centers/{center_id}?status=confirmed&sort=duration")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert [s["duration"] for s in data["sessions"]] == [30, 60]
    assert [s["student_name"] for s in data["sessions"]] == ["Aisha", "Zara"]


def test_get_center_invalid_sort_value(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    response = client.get(f"/centers/{center_id}?sort=city")
    assert response.status_code == 422


def test_get_center_not_found(client):
    response = client.get("/centers/999")
    assert response.status_code == 404


# =====================================================================
# Endpoint 4: DELETE /centers/{center_id} (delete_center)
# =====================================================================

def test_delete_center_cascades_and_removes_roster(client):
    center_res = client.post("/centers", json={"name": "Brightpath", "city": "Nagpur"})
    center_id = center_res.json()["id"]

    client.post(
        f"/centers/{center_id}/sessions",
        json={"student_name": "Aisha", "status": "confirmed", "duration": 45},
    )

    delete_res = client.delete(f"/centers/{center_id}")
    assert delete_res.status_code == 204
    assert delete_res.text == ""

    # Verify the center is removed
    get_res = client.get(f"/centers/{center_id}")
    assert get_res.status_code == 404


def test_delete_center_not_found(client):
    response = client.delete("/centers/999")
    assert response.status_code == 404