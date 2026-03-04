"""
Database connection and session management for the Resident Directory backend.
Uses SQLAlchemy with PostgreSQL via environment variables for configuration.
Environment variables are loaded from a .env file via python-dotenv.
"""
import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from .env (no-op if already set in the environment)
load_dotenv()

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Build the database URL from environment variables.
#
# POSTGRES_URL may be:
#   (a) A full connection string: "postgresql://user:pass@host:port/dbname"
#       or "postgresql://host:port/dbname" — use it directly.
#   (b) Just a hostname or IP address: "localhost" or "db.example.com"
#       — build the full URL from the individual component env vars.
#
# Required component vars (used when POSTGRES_URL is a hostname only):
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT
#
# These are set externally; do NOT hard-code credentials here.
# -------------------------------------------------------------------------

POSTGRES_URL = os.getenv("POSTGRES_URL") or ""

# Determine whether POSTGRES_URL is already a complete connection string
_is_full_url = POSTGRES_URL.startswith("postgresql://") or POSTGRES_URL.startswith("postgres://")

if _is_full_url:
    # Use the provided full DSN directly
    DATABASE_URL = POSTGRES_URL
    logger.debug("Using POSTGRES_URL as a full connection string.")
else:
    # Build the DSN from individual component variables
    _user = os.getenv("POSTGRES_USER") or "appuser"
    _password = os.getenv("POSTGRES_PASSWORD") or "dbuser123"
    _db = os.getenv("POSTGRES_DB") or "myapp"
    _host = POSTGRES_URL or "localhost"

    # POSTGRES_PORT may be empty/whitespace; fall back to the database container port
    _raw_port = os.getenv("POSTGRES_PORT") or ""
    _port = _raw_port.strip() or "5000"

    DATABASE_URL = (
        f"postgresql://{_user}:{_password}"
        f"@{_host}:{_port}/{_db}"
    )
    logger.debug("Built DATABASE_URL from component env vars (host=%s, port=%s, db=%s).", _host, _port, _db)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# PUBLIC_INTERFACE
def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session.
    Ensures the session is always closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
