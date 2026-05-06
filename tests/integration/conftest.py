import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import get_db
from app.main import app


def _get_backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _get_integration_database_url() -> URL:
    database_url = (
        os.getenv("INTEGRATION_DATABASE_URL")
        or settings.integration_database_url
        or settings.database_url
    )
    if not database_url:
        raise pytest.UsageError(
            "Integration tests require an explicit database URL. Set INTEGRATION_DATABASE_URL "
            "or DATABASE_URL to a PostgreSQL database whose user can create and drop databases."
        )

    return make_url(database_url)


def _get_admin_database_url(base_url: URL) -> URL:
    return base_url.set(database="postgres")


def _configuration_error_message(database_url: URL, error: OperationalError) -> str:
    username = database_url.username or "<unknown>"
    host = database_url.host or "<unknown>"
    port = database_url.port or "<default>"
    database = database_url.database or "<unknown>"
    return (
        "Integration database connection failed for "
        f"'{username}@{host}:{port}/{database}'. "
        "Set INTEGRATION_DATABASE_URL or DATABASE_URL to valid PostgreSQL credentials with "
        "CREATE DATABASE and DROP DATABASE privileges. "
        f"Original error: {error}"
    )


def _upgrade_database(database_url: str) -> None:
    backend_root = _get_backend_root()
    alembic_config = Config(str(backend_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_config.attributes["database_url"] = database_url
    command.upgrade(alembic_config, "head")


@pytest.fixture()
def integration_engine() -> Iterator[Engine]:
    base_url = _get_integration_database_url()
    database_name = f"test_tdd_{uuid4().hex}"
    test_database_url = base_url.set(database=database_name)
    admin_engine = create_engine(_get_admin_database_url(base_url), isolation_level="AUTOCOMMIT")
    engine: Engine | None = None

    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {database_name} TEMPLATE template0"))
    except OperationalError as error:
        admin_engine.dispose()
        pytest.fail(_configuration_error_message(base_url, error))

    database_url = test_database_url.render_as_string(hide_password=False)
    try:
        _upgrade_database(database_url)
        engine = create_engine(test_database_url, pool_pre_ping=True)
        yield engine
    except OperationalError as error:
        pytest.fail(_configuration_error_message(base_url, error))
    finally:
        if engine is not None:
            engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f"DROP DATABASE IF EXISTS {database_name}"))
        admin_engine.dispose()


@pytest.fixture()
def integration_client(integration_engine: Engine) -> Iterator[TestClient]:
    testing_session_local = sessionmaker(bind=integration_engine, autocommit=False, autoflush=False)

    def override_get_db() -> Iterator[Session]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)