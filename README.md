## Backend (FastAPI)

FastAPI backend for the finance app with JWT auth, users, and todos. Uses SQLAlchemy for ORM, Uvicorn for ASGI, and SlowAPI for rate limiting.

## Tech stack

- **FastAPI**
- **SQLAlchemy** + **psycopg2-binary** (PostgreSQL)
- **Alembic** (migrations)
- **PyJWT** + **passlib[bcrypt]** (auth)
- **SlowAPI** (rate limiting)
- **Uvicorn** (ASGI)
- **python-dotenv** (env loading)

## Project structure

```text
backend/
  app/
    api.py                # Router registration
    main.py               # App entrypoint
    logging.py            # Logging configuration
    rate_limiter.py       # SlowAPI limiter
    database/
      core.py             # Engine/session, DATABASE_URL loading
    entities/             # SQLAlchemy models (User, Todo)
    auth/                 # Auth routes/services/models
    users/                # User routes/services/models
    todos/                # Todo routes/services/models
  requirements.txt
  README.md
```

## Prerequisites

- Python 3.10+
- PostgreSQL (recommended) or SQLite for local/dev

## Setup

```powershell
# from backend/
py -3 -m venv .venv
./.venv/Scripts/Activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

- Create a `.env` in `backend/` (same folder as `requirements.txt`). Preferred:

```env
# Preferred (used first)
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require

# Backwards compat (fallback)
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

- The app reads `DATABASE_CONNECTION_STRING` first, then `DATABASE_URL`, else defaults to local SQLite.
- For production, replace the hardcoded JWT secret in `app/auth/service.py` with a secret from your environment/secret manager.

## Running (development)

```powershell
# from backend/
python -m uvicorn app.main:app --reload
```

- API Docs: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Neon (PostgreSQL) setup

1. Create a Neon project and database. Copy the SQLAlchemy/psycopg URL. It should look like:
   `postgresql://<user>:<password>@<neon-host>/<db>?sslmode=require`

2. Set the connection string

- .env (recommended): set `DATABASE_CONNECTION_STRING` as shown above.
- Windows PowerShell (current session):

```powershell
$env:DATABASE_CONNECTION_STRING = "postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
```

- Windows persistent user env:

```powershell
setx DATABASE_CONNECTION_STRING "postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
```

3. Verify connectivity

```powershell
python - << 'PY'
import os
from sqlalchemy import create_engine, text
e = create_engine(os.getenv('DATABASE_CONNECTION_STRING'))
with e.connect() as c:
    print(c.scalar(text('select 1')))
PY
```

Notes

- SSL is enforced automatically if not specified in the URL.
- Connection pool health checks are enabled via `pool_pre_ping=True`.

## Database

- SQLAlchemy engine/session are configured in `app/database/core.py`.
- `Base.metadata.create_all(...)` is intentionally commented in `app/main.py` to avoid unintended table creation.
  Use Alembic for migrations, or temporarily enable it for quick local bootstrapping.

## Endpoints (overview)

- **Auth** (`/auth`)
  - `POST /auth/` – register user (rate limited)
  - `POST /auth/token` – obtain access token (OAuth2 password flow)
- **Users** (`/users`)
  - `GET /users/me` – current user profile (Bearer auth)
  - `PUT /users/change-password` – change password (Bearer auth)
- **Todos** (`/todos`)
  - `GET /todos/` – list
  - `POST /todos/` – create
  - `GET /todos/{id}` – fetch by id
  - `PUT /todos/{id}` – update
  - `PUT /todos/{id}/complete` – mark complete
  - `DELETE /todos/{id}` – delete

## Notes

- Logging level is set in `app/main.py` via `configure_logging(LogLevels.info)`.
- SlowAPI rate limiting is configured in `app/rate_limiter.py` and applied to selected routes.
