"""
Authentication router providing login (token) and registration endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=schemas.Token,
    summary="Login – obtain a JWT access token",
    description=(
        "Authenticate with username and password using OAuth2 password flow. "
        "Returns a JWT bearer token to be sent in the Authorization header."
    ),
)
# PUBLIC_INTERFACE
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and return a JWT access token.

    - **username**: account username
    - **password**: account password

    Returns a bearer token valid for ACCESS_TOKEN_EXPIRE_MINUTES minutes.
    """
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new user with role 'resident'. "
        "Email and username must be unique. "
        "Admin accounts must be created by an existing admin."
    ),
)
# PUBLIC_INTERFACE
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - **email**: unique email address
    - **username**: unique username
    - **password**: plain-text password (min 6 chars)
    - **role**: 'resident' (default) or 'admin'

    Returns the created user object (without password).
    """
    # Check for duplicates
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Only allow role 'resident' via public registration
    role = "resident"

    user = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=auth.get_password_hash(user_in.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get(
    "/me",
    response_model=schemas.UserOut,
    summary="Get current authenticated user",
    description="Return the profile of the currently authenticated user.",
)
# PUBLIC_INTERFACE
def get_me(current_user: models.User = Depends(auth.get_current_active_user)):
    """
    Return the authenticated user's own profile.

    Requires a valid bearer token in the Authorization header.
    """
    return current_user
