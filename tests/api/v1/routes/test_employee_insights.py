from fastapi.testclient import TestClient


def _create_employee(employee_client: TestClient, **overrides: object) -> dict[str, object]:
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

    response = employee_client.post("/api/v1/employees", json=payload)

    assert response.status_code == 201

    return response.json()


def test_get_employee_insights_overview_returns_empty_metrics(employee_client: TestClient) -> None:
    response = employee_client.get("/api/v1/insights/overview")

    assert response.status_code == 200
    assert response.json() == {
        "filters": {"country": None, "job_title": None},
        "employee_count": 0,
        "currency": "USD",
        "min_salary": None,
        "max_salary": None,
        "average_salary": None,
        "median_salary": None,
        "p25_salary": None,
        "p75_salary": None,
        "salary_range": None,
        "last_updated_at": None,
    }


def test_get_employee_insights_overview_returns_filtered_salary_metrics(employee_client: TestClient) -> None:
    _create_employee(employee_client, first_name="Ada", last_name="Byron", salary="100000.00")
    _create_employee(employee_client, first_name="Ada", last_name="Lovelace", salary="200000.00")
    _create_employee(employee_client, first_name="Grace", last_name="Hopper", salary="300000.00")
    _create_employee(
        employee_client,
        first_name="Katherine",
        last_name="Johnson",
        country="United States",
        salary="400000.00",
    )

    response = employee_client.get(
        "/api/v1/insights/overview",
        params={"country": "United Kingdom", "job_title": "Engineer"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["filters"] == {"country": "United Kingdom", "job_title": "Engineer"}
    assert body["employee_count"] == 3
    assert body["currency"] == "USD"
    assert float(body["min_salary"]) == 100000.00
    assert float(body["max_salary"]) == 300000.00
    assert float(body["average_salary"]) == 200000.00
    assert float(body["median_salary"]) == 200000.00
    assert float(body["p25_salary"]) == 150000.00
    assert float(body["p75_salary"]) == 250000.00
    assert float(body["salary_range"]) == 200000.00
    assert body["last_updated_at"] is not None


def test_list_country_insights_returns_paginated_metrics(employee_client: TestClient) -> None:
    _create_employee(employee_client, country="United Kingdom", salary="100000.00")
    _create_employee(employee_client, country="United Kingdom", salary="200000.00")
    _create_employee(employee_client, country="United States", salary="300000.00")
    _create_employee(employee_client, country="United States", salary="500000.00")

    response = employee_client.get(
        "/api/v1/insights/by-country",
        params={"limit": 1, "offset": 0},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["country"] == "United States"
    assert body["items"][0]["employee_count"] == 2
    assert float(body["items"][0]["average_salary"]) == 400000.00
    assert float(body["items"][0]["median_salary"]) == 400000.00
    assert float(body["items"][0]["p25_salary"]) == 350000.00
    assert float(body["items"][0]["p75_salary"]) == 450000.00
    assert body["items"][0]["currency"] == "USD"


def test_list_job_title_insights_within_country_returns_paginated_metrics(employee_client: TestClient) -> None:
    _create_employee(employee_client, country="United Kingdom", job_title="Engineer", salary="100000.00")
    _create_employee(employee_client, country="United Kingdom", job_title="Engineer", salary="200000.00")
    _create_employee(employee_client, country="United Kingdom", job_title="Manager", salary="300000.00")
    _create_employee(employee_client, country="United Kingdom", job_title="Manager", salary="500000.00")
    _create_employee(employee_client, country="United States", job_title="Engineer", salary="700000.00")

    response = employee_client.get(
        "/api/v1/insights/by-country/United Kingdom/job-titles",
        params={"limit": 1, "offset": 1},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["job_title"] == "Engineer"
    assert body["items"][0]["employee_count"] == 2
    assert float(body["items"][0]["min_salary"]) == 100000.00
    assert float(body["items"][0]["max_salary"]) == 200000.00
    assert float(body["items"][0]["average_salary"]) == 150000.00
    assert float(body["items"][0]["median_salary"]) == 150000.00
    assert float(body["items"][0]["salary_range"]) == 100000.00
    assert body["items"][0]["currency"] == "USD"