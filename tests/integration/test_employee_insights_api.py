import pytest
from fastapi.testclient import TestClient


def _create_employee(integration_client: TestClient, **overrides: object) -> dict[str, object]:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "job_title": "Engineer",
        "department": "Platform",
        "country": "United Kingdom",
        "salary": "125000.00",
        "hire_date": "2024-01-15",
    }
    payload.update(overrides)

    response = integration_client.post("/api/v1/employees", json=payload)

    assert response.status_code == 201

    return response.json()


@pytest.mark.integration
def test_employee_insights_overview_returns_expected_metrics(integration_client: TestClient) -> None:
    _create_employee(integration_client, first_name="Ada", last_name="Byron", salary="100000.00")
    _create_employee(integration_client, first_name="Ada", last_name="Lovelace", salary="200000.00")
    _create_employee(integration_client, first_name="Grace", last_name="Hopper", salary="300000.00")
    _create_employee(
        integration_client,
        first_name="Katherine",
        last_name="Johnson",
        country="United States",
        salary="400000.00",
    )

    response = integration_client.get(
        "/api/v1/insights/overview",
        params={"country": "United Kingdom", "job_title": "Engineer"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["employee_count"] == 3
    assert float(body["average_salary"]) == 200000.00
    assert float(body["median_salary"]) == 200000.00
    assert float(body["p25_salary"]) == 150000.00
    assert float(body["p75_salary"]) == 250000.00
    assert body["last_updated_at"] is not None


@pytest.mark.integration
def test_employee_insights_by_country_returns_ranked_metrics(integration_client: TestClient) -> None:
    _create_employee(integration_client, country="United Kingdom", salary="100000.00")
    _create_employee(integration_client, country="United Kingdom", salary="200000.00")
    _create_employee(integration_client, country="United States", salary="300000.00")
    _create_employee(integration_client, country="United States", salary="500000.00")

    response = integration_client.get("/api/v1/insights/by-country")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["items"][0]["country"] == "United States"
    assert float(body["items"][0]["average_salary"]) == 400000.00
    assert body["items"][1]["country"] == "United Kingdom"
    assert float(body["items"][1]["average_salary"]) == 150000.00