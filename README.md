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

## OpenAI Integration

The backend includes comprehensive OpenAI API integration with best practices:

### Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
   Create a `.env` file in the `backend/` directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORGANIZATION=your-org-id-if-applicable
OPENAI_TIMEOUT=60.0
OPENAI_MAX_RETRIES=3

# Finance Advisor Configuration
FINANCE_ADVISOR_MODEL=o3-mini
FINANCE_ADVISOR_TEMPERATURE=0.7
FINANCE_ADVISOR_MAX_TOKENS=2000

# Optional: Azure OpenAI
# AZURE_OPENAI_API_KEY=your-azure-openai-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_VERSION=2023-07-01-preview
```

### Features

- **Chat Completions**: `/openai/chat/completions`
- **Streaming Chat**: `/openai/chat/completions/stream`
- **Embeddings**: `/openai/embeddings`
- **Image Generation**: `/openai/images/generations`
- **Content Moderation**: `/openai/moderations`
- **Model Management**: `/openai/models`
- **Health Check**: `/openai/health`

### Finance Advisor AI (o3-mini)

Specialized financial advice endpoints using o3-mini model:

- **Financial Advice**: `/finance-advisor/advice`
- **Risk Assessment**: `/finance-advisor/risk-assessment`
- **Concept Explanations**: `/finance-advisor/explain-concept`
- **Capabilities**: `/finance-advisor/capabilities`
- **Health Check**: `/finance-advisor/health`

### Rate Limiting

- Chat completions: 20 requests/minute
- Embeddings: 30 requests/minute
- Image generation: 5 requests/minute
- Model operations: 10-30 requests/minute
- **Finance Advisor**: 15 requests/minute (advice), 10/minute (risk assessment), 20/minute (explanations)

### Error Handling

The API includes comprehensive error handling with:

- Automatic retries with exponential backoff
- Rate limit detection and handling
- Authentication error handling
- Connection timeout management
- Structured error responses

### Best Practices Implemented

- ✅ Async/await support for concurrent requests
- ✅ Automatic retry logic with exponential backoff
- ✅ Rate limiting and quota management
- ✅ Structured logging and monitoring
- ✅ Input validation with Pydantic models
- ✅ Environment-based configuration
- ✅ Connection pooling and timeouts
- ✅ Comprehensive error handling

### Finance Advisor AI Features

The Finance Advisor AI is a specialized service using the o3-mini model with comprehensive financial education prompts:

#### Capabilities

- **Educational Focus**: Provides general financial knowledge and concepts
- **Risk Management**: Emphasizes conservative approaches and risk awareness
- **Regulatory Compliance**: Includes proper disclaimers and professional consultation reminders
- **Contextual Responses**: Adapts advice based on user knowledge level and query type

#### Specializations

- Investment basics and portfolio theory
- Debt management and payoff strategies
- Budgeting and expense tracking
- Retirement planning fundamentals
- Risk tolerance assessment
- Financial concept explanations

#### Safety Features

- Always includes risk warnings and disclaimers
- Never guarantees returns or specific outcomes
- Promotes consultation with licensed professionals
- Educational and informational purposes only
- Conservative investment recommendations

## Notes

- Logging level is set in `app/main.py` via `configure_logging(LogLevels.info)`.
- SlowAPI rate limiting is configured in `app/rate_limiter.py` and applied to selected routes.
