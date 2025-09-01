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
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

- The current default in `app/database/core.py` points to:
  `postgresql://postgres:postgres@db:5432/cleanfastapi`.
  Define `DATABASE_URL` in `.env` to override it, or adjust the file if needed.
- For production, replace the hardcoded JWT secret in `app/auth/service.py` with a secret from your environment/secret manager.

## Running (development)

```powershell
# from backend/
python -m uvicorn app.main:app --reload
```

- API Docs: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

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
