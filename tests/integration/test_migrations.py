import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@pytest.mark.integration
def test_users_table_matches_latest_migration(integration_engine: Engine) -> None:
    inspector = inspect(integration_engine)

    assert "users" in inspector.get_table_names()

    column_names = {column["name"] for column in inspector.get_columns("users")}
    assert column_names == {"id", "email", "full_name", "is_active", "created_at"}

    indexes = inspector.get_indexes("users")
    assert any(index["name"] == "ix_users_email" and index.get("unique") for index in indexes)


@pytest.mark.integration
def test_employees_table_matches_latest_migration(integration_engine: Engine) -> None:
    inspector = inspect(integration_engine)

    assert "employees" in inspector.get_table_names()

    column_names = {column["name"] for column in inspector.get_columns("employees")}
    assert column_names == {
        "id",
        "first_name",
        "last_name",
        "full_name",
        "job_title",
        "department",
        "country",
        "salary",
        "currency",
        "hire_date",
        "created_at",
        "updated_at",
    }

    indexes = {index["name"] for index in inspector.get_indexes("employees")}
    assert "idx_salary_insights_composite" in indexes
    assert "idx_employees_country" in indexes
    assert "idx_employees_job_title" in indexes

    with integration_engine.connect() as connection:
        trigger_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid = 'employees'::regclass AND NOT tgisinternal"
                )
            )
        }

    assert "update_employees_modtime" in trigger_names
