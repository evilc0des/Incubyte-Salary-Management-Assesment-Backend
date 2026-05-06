from fastapi.testclient import TestClient


def test_swagger_ui_is_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text
    assert "Salary Management HR Dashboard API" in response.text


def test_redoc_is_available(client: TestClient) -> None:
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "ReDoc" in response.text


def test_openapi_schema_exposes_api_metadata(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    body = response.json()

    assert body["info"] == {
        "title": "Salary Management HR Dashboard API",
        "description": (
            "Live API documentation for employee management and salary insights endpoints "
            "used by HR managers overseeing large organizations."
        ),
        "version": "1.0.0",
    }
    assert body["tags"] == [
        {
            "name": "root",
            "description": "Application entrypoint and basic service metadata.",
        },
        {
            "name": "health",
            "description": "Operational health endpoints for service monitoring.",
        },
        {
            "name": "employees",
            "description": "Employee CRUD endpoints.",
        },
        {
            "name": "insights",
            "description": "Salary analytics and reporting endpoints.",
        },
    ]