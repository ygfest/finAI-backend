"""
Database Configuration Module

Handles database connections, session management, and utilities for 
PostgreSQL (Neon) and SQLite databases.
"""

import os
import logging
from typing import Annotated, Generator, Optional
from contextlib import contextmanager

from fastapi import Depends, HTTPException, status
from sqlalchemy import create_engine, event, exc, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def get_database_url() -> str:
    """Get database URL from environment variables with fallback logic."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info("Using DATABASE_URL from environment")
        return database_url
    
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        logger.info("Using POSTGRES_URL from environment")
        return postgres_url
    
    logger.warning("No PostgreSQL URL found, falling back to SQLite for development")
    return "sqlite:///./finance_app.db"


def get_database_config() -> dict:
    """Get database configuration parameters from environment variables."""
    return {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        "echo": os.getenv("DB_ECHO", "False").lower() == "true",
    }


# =============================================================================
# DATABASE ENGINE CONFIGURATION
# =============================================================================

# Get database URL and configuration
DATABASE_URL = get_database_url()
DB_CONFIG = get_database_config()

# Determine database type for conditional configuration
is_postgresql = DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://"))
is_sqlite = DATABASE_URL.startswith("sqlite://")

logger.info(f"Database type: {'PostgreSQL' if is_postgresql else 'SQLite' if is_sqlite else 'Unknown'}")


def create_database_engine() -> Engine:
    """
    Create and configure the SQLAlchemy database engine.
    
    The engine is the entry point to the database. It maintains a pool of 
    connections and provides a source of database connectivity and behavior.
    
    Returns:
        Engine: Configured SQLAlchemy engine
        
    Key Configuration Concepts:
    - pool_pre_ping: Validates connections before use (prevents stale connections)
    - pool_recycle: Prevents connections from becoming stale
    - SSL: Required for Neon and most production PostgreSQL instances
    - Connection pooling: Manages multiple database connections efficiently
    """
    
    # Base engine configuration that applies to all database types
    engine_config = {
        "echo": DB_CONFIG["echo"],  # Log SQL queries (useful for debugging)
        "future": True,             # Use SQLAlchemy 2.0 style
    }
    
    if is_postgresql:
        logger.info("Configuring PostgreSQL engine with connection pooling")
        
        # PostgreSQL-specific configuration
        engine_config.update({
            # Connection Pool Configuration
            # ============================
            "poolclass": QueuePool,                    # Use queue-based connection pool
            "pool_size": DB_CONFIG["pool_size"],       # Base number of connections to maintain
            "max_overflow": DB_CONFIG["max_overflow"], # Additional connections when needed
            "pool_timeout": DB_CONFIG["pool_timeout"], # Seconds to wait for a connection
            "pool_recycle": DB_CONFIG["pool_recycle"], # Recycle connections after this time
            "pool_pre_ping": True,                     # Test connections before use
            
            # Connection Arguments for PostgreSQL/psycopg2
            # ===========================================
            "connect_args": {
                # SSL Configuration (required for Neon)
                "sslmode": "require",           # Require SSL connection
                "connect_timeout": 10,          # Connection timeout in seconds
                "application_name": "FinanceApp", # Application identifier in logs
            }
        })
        
        # Ensure SSL is configured if not already in URL
        if "sslmode=" not in DATABASE_URL:
            logger.info("Adding SSL requirement to PostgreSQL connection")
    
    elif is_sqlite:
        logger.info("Configuring SQLite engine for development")
        
        # SQLite-specific configuration
        engine_config.update({
            # SQLite doesn't support connection pooling in the traditional sense
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,  # Allow SQLite to be used across threads
                "timeout": 20,               # Database lock timeout
            }
        })
    
    # Create the engine with our configuration
    try:
        engine = create_engine(DATABASE_URL, **engine_config)
        logger.info("Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


# Create the global database engine instance
# ==========================================
# This engine will be used throughout the application
# It's created once at startup and reused for all database operations
engine = create_database_engine()


# =============================================================================
# SESSION CONFIGURATION
# =============================================================================

def create_session_factory() -> sessionmaker:
    """
    Create a session factory for database operations.
    
    A Session is SQLAlchemy's "handle" to the database. It represents a 
    workspace for your objects, and provides methods to query and manipulate data.
    
    Returns:
        sessionmaker: Factory for creating database sessions
        
    Key Session Concepts:
    - autocommit=False: Transactions must be explicitly committed
    - autoflush=False: Don't automatically flush changes to database
    - expire_on_commit=False: Keep objects accessible after commit
    """
    return sessionmaker(
        bind=engine,                    # Bind to our database engine
        autocommit=False,              # Require explicit transaction commits
        autoflush=False,               # Don't auto-flush changes
        expire_on_commit=False,        # Keep objects accessible after commit
    )


# Create the session factory
# ==========================
# This factory will be used to create individual database sessions
SessionLocal = create_session_factory()


# =============================================================================
# ORM BASE CLASS
# =============================================================================

# Create the base class for all ORM models
# ========================================
# All your database models (User, Todo, etc.) should inherit from this Base
Base = declarative_base()

# Add metadata for the base class
Base.metadata.bind = engine


# =============================================================================
# DATABASE SESSION DEPENDENCY
# =============================================================================

def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency function that provides database sessions to FastAPI routes.
    
    This is a FastAPI dependency that:
    1. Creates a new database session
    2. Yields it to the route function
    3. Automatically closes the session when done
    4. Handles any exceptions that occur
    
    Yields:
        Session: SQLAlchemy database session
        
    Example usage in a FastAPI route:
    ```python
    @app.get("/users/")
    async def get_users(db: DbSession):
        users = db.query(User).all()
        return users
    ```
    
    Key Concepts:
    - Generator function: Uses 'yield' instead of 'return'
    - Context management: Automatically handles cleanup
    - Exception safety: Ensures sessions are always closed
    """
    # Create a new database session
    session = SessionLocal()
    
    try:
        # Log successful connection (remove in production)
        logger.debug("Database session created")
        
        # Yield the session to the calling function
        # The route function will receive this session as a parameter
        yield session
        
        # After the route function completes, execution continues here
        logger.debug("Database session completed successfully")
        
    except exc.SQLAlchemyError as e:
        # Handle SQLAlchemy-specific errors
        logger.error(f"Database error occurred: {e}")
        
        # Rollback any pending transaction
        session.rollback()
        
        # Re-raise as HTTP exception for FastAPI to handle
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed"
        )
        
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error in database session: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
        
    finally:
        # Always close the session, regardless of success or failure
        # This ensures we don't leak database connections
        session.close()
        logger.debug("Database session closed")


# =============================================================================
# TYPE ANNOTATIONS FOR DEPENDENCY INJECTION
# =============================================================================

# Create a type annotation for database sessions
# ==============================================
# This provides type hints for FastAPI route parameters
# It combines the Session type with the dependency injection
DbSession = Annotated[Session, Depends(get_database_session)]

"""
Usage example in your FastAPI routes:

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: DbSession):
    # 'db' is automatically injected as a database session
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
"""


# =============================================================================
# DATABASE UTILITIES AND HEALTH CHECKS
# =============================================================================

@contextmanager
def get_db_context():
    """
    Context manager for database operations outside of FastAPI routes.
    
    Use this when you need a database session in background tasks,
    startup events, or other non-route contexts.
    
    Example:
    ```python
    with get_db_context() as db:
        user = db.query(User).first()
        print(user.name)
    ```
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
        
    This function is useful for:
    - Health checks
    - Startup verification
    - Monitoring and alerting
    """
    try:
        with get_db_context() as db:
            # Execute a simple query to test the connection
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            
        logger.info("Database connection check: SUCCESS")
        return True
        
    except Exception as e:
        logger.error(f"Database connection check: FAILED - {e}")
        return False


def get_database_info() -> dict:
    """
    Get information about the current database configuration.
    
    Returns:
        dict: Database configuration information
        
    Useful for debugging and monitoring.
    """
    return {
        "database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,  # Hide credentials
        "database_type": "PostgreSQL" if is_postgresql else "SQLite" if is_sqlite else "Unknown",
        "pool_size": DB_CONFIG["pool_size"] if is_postgresql else "N/A",
        "max_overflow": DB_CONFIG["max_overflow"] if is_postgresql else "N/A",
        "pool_timeout": DB_CONFIG["pool_timeout"] if is_postgresql else "N/A",
        "pool_recycle": DB_CONFIG["pool_recycle"] if is_postgresql else "N/A",
        "echo_sql": DB_CONFIG["echo"],
    }


# =============================================================================
# DATABASE EVENT LISTENERS
# =============================================================================

if is_postgresql:
    @event.listens_for(engine, "connect")
    def set_postgresql_search_path(dbapi_connection, connection_record):
        """
        Set PostgreSQL-specific configuration when a connection is established.
        
        This function runs every time a new database connection is created.
        It's useful for setting session-level configuration.
        
        Args:
            dbapi_connection: The raw database connection
            connection_record: SQLAlchemy's connection record
        """
        try:
            with dbapi_connection.cursor() as cursor:
                # Set the search path (schema) if needed
                # cursor.execute("SET search_path TO public")
                
                # Set timezone to UTC for consistency
                cursor.execute("SET timezone TO 'UTC'")
                
                # Set statement timeout to prevent long-running queries
                cursor.execute("SET statement_timeout = '30s'")
                
            logger.debug("PostgreSQL connection configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure PostgreSQL connection: {e}")


# =============================================================================
# STARTUP VALIDATION
# =============================================================================

def validate_database_setup():
    """
    Validate that the database is properly configured and accessible.
    
    This function should be called during application startup to ensure
    everything is working correctly before accepting requests.
    
    Raises:
        Exception: If database setup validation fails
    """
    logger.info("Validating database setup...")
    
    # Check basic connection
    if not check_database_connection():
        raise Exception("Database connection failed")
    
    # Log configuration info
    db_info = get_database_info()
    logger.info(f"Database configuration: {db_info}")
    
    # Additional PostgreSQL-specific checks
    if is_postgresql:
        try:
            with get_db_context() as db:
                # Check PostgreSQL version
                result = db.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL version: {version}")
                
                # Check if we can create tables (permissions check)
                # This doesn't actually create a table, just checks permissions
                db.execute(text("SELECT 1 WHERE has_table_privilege(current_user, 'information_schema.tables', 'select')"))
                
        except Exception as e:
            logger.warning(f"PostgreSQL validation warning: {e}")
    
    logger.info("Database setup validation completed successfully")


# =============================================================================
# EXPORT COMMONLY USED ITEMS
# =============================================================================

# These are the main items other modules will import
__all__ = [
    "engine",                    # Database engine
    "SessionLocal",             # Session factory
    "Base",                     # ORM base class
    "get_database_session",     # Dependency function
    "DbSession",                # Type annotation
    "get_db_context",           # Context manager
    "check_database_connection", # Health check
    "get_database_info",        # Configuration info
    "validate_database_setup",  # Startup validation
]

"""
Quick Reference for Using This Module:

1. In your FastAPI routes:
   ```python
   from app.database.core import DbSession
   
   @router.get("/users/")
   async def get_users(db: DbSession):
       return db.query(User).all()
   ```

2. In background tasks or startup:
   ```python
   from app.database.core import get_db_context
   
   with get_db_context() as db:
       # Your database operations here
       pass
   ```

3. For health checks:
   ```python
   from app.database.core import check_database_connection
   
   if check_database_connection():
       print("Database is healthy")
   ```

4. In your main.py for startup validation:
   ```python
   from app.database.core import validate_database_setup
   
   @app.on_event("startup")
   async def startup_event():
       validate_database_setup()
   ```
"""
