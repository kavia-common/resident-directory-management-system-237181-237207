"""
Admin router providing user management endpoints for admin users.
All endpoints in this router require admin role.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_user_or_404(user_id: int, db: Session) -> models.User:
    """Fetch a user by ID or raise 404."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/users",
    response_model=List[schemas.AdminUserOut],
    summary="List all users (admin only)",
    description="Retrieve a paginated list of all user accounts. Admin access required.",
)
# PUBLIC_INTERFACE
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    List all user accounts.

    Admin only. Supports pagination.
    """
    return db.query(models.User).offset(skip).limit(limit).all()


@router.get(
    "/users/{user_id}",
    response_model=schemas.AdminUserOut,
    summary="Get a user by ID (admin only)",
    description="Retrieve full account details for a specific user. Admin access required.",
)
# PUBLIC_INTERFACE
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """Return a user account by ID."""
    return _get_user_or_404(user_id, db)


@router.post(
    "/users",
    response_model=schemas.AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (admin only)",
    description="Create a new user account, including admin accounts. Admin access required.",
)
# PUBLIC_INTERFACE
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Create a new user account.

    Admin only. Unlike public registration, admins may assign any role.
    """
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Validate role
    if user_in.role not in ("admin", "resident"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'resident'")

    user = models.User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=auth.get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put(
    "/users/{user_id}",
    response_model=schemas.AdminUserOut,
    summary="Update a user account (admin only)",
    description="Update any user account field including role and active status. Admin only.",
)
# PUBLIC_INTERFACE
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Update a user account.

    Admin only. Can change email, username, password, role, and active status.
    """
    user = _get_user_or_404(user_id, db)

    # Check uniqueness for email/username changes
    if user_in.email and user_in.email != user.email:
        if db.query(models.User).filter(models.User.email == user_in.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
    if user_in.username and user_in.username != user.username:
        if db.query(models.User).filter(models.User.username == user_in.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = auth.get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account (admin only)",
    description="Permanently delete a user account. Admin access required.",
)
# PUBLIC_INTERFACE
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(auth.require_admin),
):
    """
    Delete a user account by ID.

    Admin only. Admins cannot delete their own account.
    """
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = _get_user_or_404(user_id, db)
    db.delete(user)
    db.commit()
