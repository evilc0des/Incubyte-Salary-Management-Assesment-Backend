from datetime import date

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


def _shift_month_start(value: date, months: int) -> date:
    absolute_month = (value.year * 12 + value.month - 1) + months
    year = absolute_month // 12
    month = absolute_month % 12 + 1
    return date(year, month, 1)


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


@pytest.mark.integration
def test_employee_insights_by_department_returns_grouped_metrics(integration_client: TestClient) -> None:
    _create_employee(integration_client, department="Engineering", salary="100000.00")
    _create_employee(integration_client, department="Engineering", salary="200000.00")
    _create_employee(integration_client, department="Human Resources", salary="150000.00")

    response = integration_client.get("/api/v1/insights/by-department")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["items"][0]["department"] == "Engineering"
    assert body["items"][0]["employee_count"] == 2
    assert float(body["items"][0]["average_salary"]) == 150000.00


@pytest.mark.integration
def test_employee_hiring_trend_returns_requested_month_window(integration_client: TestClient) -> None:
    current_month = date.today().replace(day=1)
    previous_month = _shift_month_start(current_month, -1)
    older_month = _shift_month_start(current_month, -5)

    _create_employee(integration_client, first_name="Ada", last_name="Current", hire_date=current_month.isoformat())
    _create_employee(integration_client, first_name="Grace", last_name="Previous", hire_date=previous_month.isoformat())
    _create_employee(integration_client, first_name="Linus", last_name="Older", hire_date=older_month.isoformat())

    response = integration_client.get("/api/v1/insights/hiring-trend", params={"months": 2})

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert [item["month"] for item in body["items"]] == [
        previous_month.strftime("%Y-%m"),
        current_month.strftime("%Y-%m"),
    ]
    assert [item["hires_count"] for item in body["items"]] == [1, 1]