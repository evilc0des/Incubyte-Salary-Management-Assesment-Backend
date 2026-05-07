from app.core.config import normalize_postgres_database_url


def test_normalize_postgres_database_url_rewrites_plain_postgresql_scheme() -> None:
    database_url = "postgresql://user:pass@db.example.com:5432/app_db"

    assert normalize_postgres_database_url(database_url) == (
        "postgresql+psycopg://user:pass@db.example.com:5432/app_db"
    )


def test_normalize_postgres_database_url_rewrites_railway_postgres_scheme() -> None:
    database_url = "postgres://user:pass@db.example.com:5432/app_db?sslmode=require"

    assert normalize_postgres_database_url(database_url) == (
        "postgresql+psycopg://user:pass@db.example.com:5432/app_db?sslmode=require"
    )


def test_normalize_postgres_database_url_keeps_explicit_driver_scheme() -> None:
    database_url = "postgresql+psycopg://user:pass@db.example.com:5432/app_db"

    assert normalize_postgres_database_url(database_url) == database_url