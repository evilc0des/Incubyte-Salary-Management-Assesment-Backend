# Backend

FastAPI starter with SQLAlchemy 2.x, Alembic, and PostgreSQL.

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

