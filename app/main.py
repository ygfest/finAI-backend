"""
Main FastAPI Application Module

Entry point for the Finance App API. Configures FastAPI application,
middleware, routers, and startup/shutdown events.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database.core import (
    engine,
    Base,
    validate_database_setup,
    check_database_connection,
    get_database_info,
)

# Import models to register them with SQLAlchemy
from .entities.todo import Todo
from .entities.user import User

from .api import register_routes
from .logging import configure_logging, LogLevels
from .health import router as health_router
from .openai.controller import router as openai_router
from .openai.controller import finance_router

configure_logging(LogLevels.info)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("Starting Finance App API...")
    
    try:
        logger.info("Validating database setup...")
        validate_database_setup()
        
        db_info = get_database_info()
        logger.info(f"Database Info: {db_info}")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready")
        
        logger.info("Application startup completed successfully!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Finance App API...")
    
    try:
        engine.dispose()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shutdown completed")


# =============================================================================
# FASTAPI APPLICATION CONFIGURATION
# =============================================================================

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
        
    This function:
    - Creates the FastAPI app with metadata
    - Configures CORS middleware
    - Includes all routers
    - Sets up exception handlers
    """
    
    # Create FastAPI application instance
    # ==================================
    application = FastAPI(
        # Application Metadata
        # ===================
        title="Finance Advisor API",
        description="""
        🏦 **Finance Advisor API**
        
        A comprehensive financial management API with AI-powered advice capabilities.
        
        ## Features
        
        * 🤖 **AI Financial Advisor** - Get personalized financial advice using OpenAI
        * 👤 **User Management** - Authentication and user profiles
        * 📋 **Todo Management** - Track financial tasks and goals
        * 🔒 **Secure Authentication** - JWT-based authentication
        * 📊 **Database Integration** - PostgreSQL with Neon cloud hosting
        * ⚡ **High Performance** - Async operations and connection pooling
        
        ## Getting Started
        
        1. Authenticate using `/auth/login`
        2. Use the returned JWT token in the `Authorization` header
        3. Start making requests to protected endpoints
        
        ## Database
        
        This API uses PostgreSQL hosted on Neon for production and SQLite for development.
        """,
        version="1.0.0",
        
        # API Documentation Configuration
        # ==============================
        docs_url="/docs",           # Swagger UI endpoint
        redoc_url="/redoc",         # ReDoc endpoint
        openapi_url="/openapi.json", # OpenAPI schema endpoint
        
        # Application Lifecycle
        # ====================
        lifespan=lifespan,          # Startup/shutdown events
    )
    
    return application


# Create the application instance
# ==============================
app = create_application()


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

def configure_middleware(application: FastAPI) -> None:
    """
    Configure middleware for the FastAPI application.
    
    Args:
        application: FastAPI application instance
        
    Middleware Concepts:
    - Middleware: Code that runs before/after each request
    - CORS: Cross-Origin Resource Sharing for frontend integration
    - Order matters: Middleware is applied in the order it's added
    """
    
    # CORS Middleware Configuration
    # ============================
    # This allows your frontend to communicate with the API
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    
    application.add_middleware(
        CORSMiddleware,
        # Allow origins (frontend URLs)
        allow_origins=cors_origins,  # In production, specify your frontend domains
        
        # Allow credentials (cookies, authorization headers)
        allow_credentials=True,
        
        # Allow HTTP methods
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        
        # Allow headers
        allow_headers=["*"],  # In production, be more specific
        
        # Expose headers to frontend
        expose_headers=["X-Total-Count", "X-Page-Count"],
    )
    
    logger.info(f"🌐 CORS configured for origins: {cors_origins}")


# Apply middleware configuration
configure_middleware(app)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """
    Handle internal server errors gracefully.
    
    This provides a consistent error response format and prevents
    sensitive error details from being exposed to clients.
    """
    logger.error(f"Internal server error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "type": "internal_error"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Handle HTTP exceptions with consistent formatting.
    
    This ensures all HTTP errors have a consistent response structure.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "type": "http_error"
        }
    )


# =============================================================================
# ROUTER REGISTRATION
# =============================================================================

def configure_routers(application: FastAPI) -> None:
    """
    Register all API routers with the application.
    
    Args:
        application: FastAPI application instance
        
    Router Organization:
    - Health: System health checks
    - OpenAI: AI-powered features
    - Finance: Financial advisory endpoints
    - API: Main application endpoints (users, todos, auth)
    """
    
    # Core System Routers
    # ===================
    application.include_router(
        health_router,
        tags=["Health"],
        prefix="/health"
    )
    
    # AI and External Service Routers
    # ===============================
    application.include_router(
        openai_router,
        tags=["OpenAI"],
        prefix="/api/v1"
    )
    
    application.include_router(
        finance_router,
        tags=["Finance Advisor"],
        prefix="/api/v1"
    )
    
    # Main Application Routers
    # ========================
    # This includes auth, users, todos, etc.
    register_routes(application)
    
    logger.info("🛣️  All routers registered successfully")


# Apply router configuration
configure_routers(app)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint that provides API information.
    
    This is useful for:
    - Health checks from load balancers
    - API discovery
    - Basic connectivity testing
    """
    # Check database connectivity
    db_healthy = check_database_connection()
    
    return {
        "message": "🏦 Finance Advisor API",
        "version": "1.0.0",
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "features": [
            "AI Financial Advisor",
            "User Management",
            "Todo Management",
            "JWT Authentication",
            "PostgreSQL Database",
            "Rate Limiting",
            "CORS Support"
        ]
    }


# =============================================================================
# APPLICATION INFORMATION
# =============================================================================

@app.get("/info", tags=["System"])
async def get_app_info():
    """
    Get detailed application information.
    
    This endpoint provides:
    - Database configuration (without sensitive data)
    - Environment information
    - Feature flags
    - System status
    """
    db_info = get_database_info()
    
    return {
        "application": {
            "name": "Finance Advisor API",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
        },
        "database": db_info,
        "features": {
            "ai_advisor": True,
            "user_management": True,
            "todo_system": True,
            "jwt_auth": True,
            "rate_limiting": True,
        },
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "openapi": "/openapi.json",
        }
    }


# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

if __name__ == "__main__":
    """
    Development server runner.
    
    This allows you to run the app directly with: python -m app.main
    For production, use: uvicorn app.main:app
    """
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,           # Auto-reload on code changes
        log_level="info",      # Logging level
        access_log=True,       # Log all requests
    )

"""
🚀 Quick Start Guide:

1. Set up your environment:
   - Copy `env.example` to `.env`
   - Add your Neon PostgreSQL connection string
   - Configure other environment variables

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Visit the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

5. Test the API:
   - Root endpoint: http://localhost:8000/
   - Health check: http://localhost:8000/health
   - App info: http://localhost:8000/info

📚 Learn More:
- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Neon Documentation: https://neon.tech/docs/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
"""