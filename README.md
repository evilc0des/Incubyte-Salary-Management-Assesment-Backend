# Backend

FastAPI starter with SQLAlchemy 2.x, Alembic, and PostgreSQL.

The `employees` schema uses PostgreSQL extensions managed by Alembic:

- `pgcrypto` for `gen_random_uuid()` primary keys
- `pg_trgm` for trigram-backed `full_name` search

## Run locally

1. Create a virtual environment.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`.
4. Apply migrations:

   ```powershell
   alembic upgrade head
   ```

5. Start the API:

   ```powershell
   uvicorn app.main:app --reload
   ```

6. Open the live API docs:

   ```text
   Swagger UI: http://localhost:8000/docs
   ReDoc: http://localhost:8000/redoc
   OpenAPI JSON: http://localhost:8000/openapi.json
   ```

## Seed employees

Run the employee seeder from the backend root and provide external name files:

```powershell
.\.venv\Scripts\python.exe .\scripts\seed_employees.py `
   --first-names-path <dir>\first_names.txt `
   --last-names-path <dir>\last_names.txt
```

Notes:

- Each run appends new employees; it does not delete or replace existing rows.
- The default seed count is `10000` employees.
- The script uses batched bulk inserts for regular developer use and accepts optional `--count`, `--batch-size`, and `--seed` arguments.
- Name files must contain one name per line, and each usable value must fit within the 50-character employee name columns.

## TDD workflow

1. Create and activate the backend virtual environment, then install runtime and test dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   ```

2. Run the fast API test lane:

   ```powershell
   .\scripts\run-tests.ps1
   ```

3. Run coverage for the fast lane:

   ```powershell
   .\scripts\run-tests.ps1 -Coverage
   ```

4. Run the integration lane against a reachable Postgres server:

   ```powershell
   .\scripts\run-tests.ps1 -Integration
   ```

The integration test creates its own temporary database, applies the current Alembic migrations there, verifies the schema, and then drops the database. It requires an explicit `INTEGRATION_DATABASE_URL` or `DATABASE_URL`; it does not fall back to the app's default localhost credentials. If you are working from the orchestration repository, `docker compose up -d postgres` is a convenient way to start the Postgres server locally before running the integration lane.

If the local Postgres container was initialized earlier with different credentials, point `INTEGRATION_DATABASE_URL` at the matching server credentials or recreate that local database volume before running the integration lane. The connection used for integration tests must be able to create and drop temporary databases.

Example:

```powershell
$env:INTEGRATION_DATABASE_URL = "postgresql+psycopg://app_user:app_password@localhost:5432/app_db"
.\scripts\run-tests.ps1 -Integration
```

You can also pass the URL directly to the helper:

```powershell
.\scripts\run-tests.ps1 -Integration -IntegrationDatabaseUrl "postgresql+psycopg://app_user:app_password@localhost:5432/app_db"
```

If you run `pytest` directly and see `ModuleNotFoundError: No module named 'fastapi'`, your shell is picking up a global `pytest` binary instead of the backend virtual environment. `./scripts/run-tests.ps1` avoids that by invoking `backend/.venv/Scripts/python.exe -m pytest` explicitly.

If you run `pytest --run-integration -m integration` directly and see a PostgreSQL authentication error, the integration database URL is pointing at the wrong local server or wrong credentials.


