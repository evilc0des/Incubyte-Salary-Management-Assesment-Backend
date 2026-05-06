from fastapi.testclient import TestClient


def test_root_returns_welcome_message(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI Backend"}
