import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


@pytest.mark.integration
def test_users_table_matches_latest_migration(integration_engine: Engine) -> None:
    inspector = inspect(integration_engine)

    assert "users" in inspector.get_table_names()

    column_names = {column["name"] for column in inspector.get_columns("users")}
    assert column_names == {"id", "email", "full_name", "is_active", "created_at"}

    indexes = inspector.get_indexes("users")
    assert any(index["name"] == "ix_users_email" and index.get("unique") for index in indexes)
