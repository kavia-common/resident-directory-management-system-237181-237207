"""
Authentication and authorization utilities.
Provides JWT token creation/verification, password hashing, and
FastAPI dependencies for retrieving the current authenticated user.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api import models, schemas

# -------------------------------------------------------------------------
# Configuration – read from environment variables (set in .env)
# -------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# -------------------------------------------------------------------------
# Password hashing context (bcrypt)
# -------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 bearer token scheme – the tokenUrl must match the /auth/token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The raw password provided by the user.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def get_password_hash(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        password: The raw password to hash.

    Returns:
        A bcrypt hash string.
    """
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Dictionary of claims to encode in the token (must include 'sub').
        expires_delta: Optional custom expiry duration. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# PUBLIC_INTERFACE
def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Fetch a user record by username.

    Args:
        db: Active SQLAlchemy session.
        username: The username to look up.

    Returns:
        User ORM object or None if not found.
    """
    return db.query(models.User).filter(models.User.username == username).first()


# PUBLIC_INTERFACE
def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticate a user by username and plain-text password.

    Args:
        db: Active SQLAlchemy session.
        username: The username to authenticate.
        password: The plain-text password to verify.

    Returns:
        Authenticated User ORM object, or None on failure.
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# PUBLIC_INTERFACE
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    FastAPI dependency: decode the JWT and return the authenticated User.

    Raises:
        HTTPException 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, token_data.username)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


# PUBLIC_INTERFACE
def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    FastAPI dependency: return the current user only if their account is active.

    Raises:
        HTTPException 400 if the account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# PUBLIC_INTERFACE
def require_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    FastAPI dependency: restrict access to admin users only.

    Raises:
        HTTPException 403 if the current user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
