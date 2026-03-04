"""
Resident Directory Management System – FastAPI Application Entry Point.

Provides REST API endpoints for:
  - Authentication (JWT): /auth
  - Resident profiles: /residents
  - Public directory (privacy-filtered): /directory
  - Buildings: /buildings
  - Announcements: /announcements
  - Direct messages: /messages
  - Admin user management: /admin

Authentication: OAuth2 bearer token (JWT). Obtain a token via POST /auth/token.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.database import engine, Base
from src.api.routers import auth, residents, directory, buildings, announcements, admin, messages

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAPI tags metadata
# ---------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "Authentication",
        "description": "Login (JWT token), registration, and current-user endpoints.",
    },
    {
        "name": "Residents",
        "description": "CRUD operations for resident profiles. Admins have full access; "
                       "residents may only view/update their own profile.",
    },
    {
        "name": "Directory",
        "description": "Privacy-filtered public-facing resident directory with search support.",
    },
    {
        "name": "Buildings",
        "description": "Building/complex management. Admins create/update/delete; "
                       "all authenticated users may list.",
    },
    {
        "name": "Announcements",
        "description": "Community announcements. Admins post; all authenticated users read.",
    },
    {
        "name": "Messages",
        "description": "Direct messaging between residents.",
    },
    {
        "name": "Admin",
        "description": "Admin-only user account management.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables on startup (idempotent via IF NOT EXISTS)."""
    try:
        # Create all tables that are not yet in the DB (safe for production
        # since the schema.sql already ran; this is a safety net only).
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified / created successfully.")
    except Exception as exc:
        logger.error("Database initialisation failed: %s", exc)
    yield


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Resident Directory Management System API",
    description=(
        "REST API for managing resident profiles, a searchable directory, "
        "buildings, announcements, direct messages, and role-based access control. "
        "\n\n**Default credentials (seed data):** username `admin`, password `secret`."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware – allow all origins for development; restrict in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(residents.router)
app.include_router(directory.router)
app.include_router(buildings.router)
app.include_router(announcements.router)
app.include_router(messages.router)
app.include_router(admin.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get(
    "/",
    summary="Health Check",
    description="Returns a simple healthy status message.",
    tags=["Health"],
)
# PUBLIC_INTERFACE
def health_check():
    """
    Health check endpoint.

    Returns:
        dict: ``{"message": "Healthy"}``
    """
    return {"message": "Healthy"}
