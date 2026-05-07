from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.employee import Employee
from app.seed.employees import seed_employees


def _write_names_file(path: Path, values: list[str]) -> Path:
    path.write_text("\n".join(values), encoding="utf-8")
    return path


@pytest.mark.integration
def test_seed_employees_appends_rows_and_uses_database_defaults(
    integration_engine: Engine,
    tmp_path: Path,
) -> None:
    first_names_path = _write_names_file(tmp_path / "first_names.txt", ["Ada", "Linus", "Grace"])
    last_names_path = _write_names_file(tmp_path / "last_names.txt", ["Lovelace", "Torvalds", "Hopper"])
    session_factory = sessionmaker(bind=integration_engine, autocommit=False, autoflush=False)

    first_result = seed_employees(
        session_factory,
        first_names_path=first_names_path,
        last_names_path=last_names_path,
        count=12,
        batch_size=5,
        seed=11,
    )
    second_result = seed_employees(
        session_factory,
        first_names_path=first_names_path,
        last_names_path=last_names_path,
        count=8,
        batch_size=3,
        seed=17,
    )

    assert first_result.inserted_count == 12
    assert first_result.batch_count == 3
    assert second_result.inserted_count == 8
    assert second_result.batch_count == 3

    with Session(integration_engine) as session:
        employee_count = session.scalar(select(func.count()).select_from(Employee))
        employee = session.scalar(select(Employee).order_by(Employee.created_at, Employee.id).limit(1))
        distinct_hire_dates = session.scalar(select(func.count(func.distinct(Employee.hire_date))))

    assert employee_count == 20
    assert employee is not None
    assert employee.full_name == f"{employee.first_name} {employee.last_name}"
    assert employee.currency == "USD"
    assert employee.salary > 0
    assert employee.hire_date is not None
    assert distinct_hire_dates is not None
    assert distinct_hire_dates > 1


@pytest.mark.integration
def test_employee_update_changes_updated_at(integration_engine: Engine) -> None:
    with Session(integration_engine) as session:
        employee = Employee(
            first_name="Ada",
            last_name="Lovelace",
            job_title="Engineer",
            department="Platform",
            country="United Kingdom",
            salary=100000,
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)

        original_updated_at = employee.updated_at
        employee.job_title = "Principal Engineer"
        session.commit()
        session.refresh(employee)

        assert employee.updated_at > original_updated_at