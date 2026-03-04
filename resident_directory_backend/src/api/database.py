"""
Database connection and session management for the Resident Directory backend.
Uses SQLAlchemy with PostgreSQL via environment variables for configuration.
Environment variables are loaded from a .env file via python-dotenv.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from .env (no-op if already set in the environment)
load_dotenv()

# -------------------------------------------------------------------------
# Build the database URL from environment variables.
# Required vars: POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD,
#                POSTGRES_DB, POSTGRES_PORT
# These are set externally; do NOT hard-code credentials here.
# Falls back to the seed-data defaults for local development only.
# -------------------------------------------------------------------------
POSTGRES_URL = os.getenv("POSTGRES_URL") or "localhost"
POSTGRES_USER = os.getenv("POSTGRES_USER") or "appuser"
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") or "dbuser123"
POSTGRES_DB = os.getenv("POSTGRES_DB") or "myapp"
POSTGRES_PORT = os.getenv("POSTGRES_PORT") or "5000"

# Strip any surrounding whitespace that might sneak in from the env file
POSTGRES_PORT = POSTGRES_PORT.strip()

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_URL}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

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
