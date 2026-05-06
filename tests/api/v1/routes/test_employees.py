from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient


def _create_employee(employee_client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "job_title": "Engineer",
        "department": "Platform",
        "country": "United Kingdom",
        "salary": "125000.50",
        "hire_date": "2024-01-15",
    }
    payload.update(overrides)

    response = employee_client.post("/api/v1/employees", json=payload)

    assert response.status_code == 201

    return response.json()


def test_list_employees_returns_empty_paginated_result(employee_client: TestClient) -> None:
    response = employee_client.get("/api/v1/employees")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_create_employee_returns_created_resource(employee_client: TestClient) -> None:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "job_title": "Engineer",
        "department": "Platform",
        "country": "United Kingdom",
        "salary": "125000.50",
        "hire_date": "2024-01-15",
    }

    response = employee_client.post("/api/v1/employees", json=payload)

    assert response.status_code == 201

    body = response.json()

    assert UUID(body["id"])
    assert body["first_name"] == payload["first_name"]
    assert body["last_name"] == payload["last_name"]
    assert body["full_name"] == "Ada Lovelace"
    assert body["job_title"] == payload["job_title"]
    assert body["department"] == payload["department"]
    assert body["country"] == payload["country"]
    assert float(body["salary"]) == 125000.50
    assert body["currency"] == "USD"
    assert body["hire_date"] == str(date(2024, 1, 15))
    assert body["created_at"]
    assert body["updated_at"]


def test_get_employee_by_id_returns_employee(employee_client: TestClient) -> None:
    employee = _create_employee(employee_client)

    response = employee_client.get(f"/api/v1/employees/{employee['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == employee["id"]
    assert response.json()["full_name"] == employee["full_name"]


def test_get_employee_by_id_returns_not_found_for_unknown_id(employee_client: TestClient) -> None:
    response = employee_client.get("/api/v1/employees/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee not found"}


def test_list_employees_supports_search_and_pagination(employee_client: TestClient) -> None:
    _create_employee(employee_client, last_name="Byron")
    _create_employee(employee_client, last_name="Lovelace")
    _create_employee(employee_client, first_name="Grace", last_name="Hopper")

    response = employee_client.get("/api/v1/employees", params={"search": "ada", "limit": 1, "offset": 1})

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["limit"] == 1
    assert response.json()["offset"] == 1
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["full_name"] == "Ada Lovelace"


def test_put_employee_replaces_writable_fields(employee_client: TestClient) -> None:
    employee = _create_employee(employee_client)
    payload = {
        "first_name": "Katherine",
        "last_name": "Johnson",
        "job_title": "Principal Engineer",
        "department": "Research",
        "country": "United States",
        "salary": "140000.00",
        "hire_date": "2023-10-01",
    }

    response = employee_client.put(f"/api/v1/employees/{employee['id']}", json=payload)

    assert response.status_code == 200
    assert response.json()["full_name"] == "Katherine Johnson"
    assert response.json()["job_title"] == payload["job_title"]
    assert response.json()["department"] == payload["department"]
    assert response.json()["country"] == payload["country"]
    assert float(response.json()["salary"]) == 140000.00
    assert response.json()["hire_date"] == payload["hire_date"]
    assert response.json()["currency"] == "USD"


def test_patch_employee_updates_partial_fields(employee_client: TestClient) -> None:
    employee = _create_employee(employee_client)

    response = employee_client.patch(
        f"/api/v1/employees/{employee['id']}",
        json={"department": "Applied Math", "salary": "130000.00"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == employee["full_name"]
    assert response.json()["department"] == "Applied Math"
    assert float(response.json()["salary"]) == 130000.00


def test_delete_employee_removes_employee(employee_client: TestClient) -> None:
    employee = _create_employee(employee_client)

    delete_response = employee_client.delete(f"/api/v1/employees/{employee['id']}")
    get_response = employee_client.get(f"/api/v1/employees/{employee['id']}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Employee not found"}


def test_create_employee_rejects_non_positive_salary(employee_client: TestClient) -> None:
    response = employee_client.post(
        "/api/v1/employees",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "job_title": "Engineer",
            "department": "Platform",
            "country": "United Kingdom",
            "salary": "0",
            "hire_date": "2024-01-15",
        },
    )

    assert response.status_code == 422