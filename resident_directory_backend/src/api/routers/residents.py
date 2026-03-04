"""
Residents router providing CRUD endpoints for resident profiles.
Admins can manage all residents; residents can only view/update their own profile.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/residents", tags=["Residents"])


def _get_resident_or_404(resident_id: int, db: Session) -> models.Resident:
    """Fetch a resident by ID or raise 404."""
    resident = db.query(models.Resident).filter(models.Resident.id == resident_id).first()
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")
    return resident


@router.get(
    "/",
    response_model=List[schemas.ResidentOut],
    summary="List all residents (admin only)",
    description="Retrieve a paginated list of all resident profiles. Admin access required.",
)
# PUBLIC_INTERFACE
def list_residents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    List all residents with optional filters.

    Requires admin role. Supports pagination via `skip` and `limit`.
    """
    query = db.query(models.Resident)
    if building_id is not None:
        query = query.filter(models.Resident.building_id == building_id)
    if is_active is not None:
        query = query.filter(models.Resident.is_active == is_active)
    return query.offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=schemas.ResidentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a resident profile (admin only)",
    description="Create a new resident profile record. Admin access required.",
)
# PUBLIC_INTERFACE
def create_resident(
    resident_in: schemas.ResidentCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Create a new resident profile.

    Admin only. Optionally links to an existing user account via `user_id`.
    Also creates default privacy settings for the new resident.
    """
    resident = models.Resident(**resident_in.model_dump())
    db.add(resident)
    db.flush()  # get the resident ID before committing

    # Create default privacy settings
    privacy = models.PrivacySettings(resident_id=resident.id)
    db.add(privacy)
    db.commit()
    db.refresh(resident)
    return resident


@router.get(
    "/me",
    response_model=schemas.ResidentOut,
    summary="Get own resident profile",
    description="Return the resident profile associated with the authenticated user.",
)
# PUBLIC_INTERFACE
def get_my_resident_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Return the resident profile linked to the current user account.

    Raises 404 if the user has no linked resident profile.
    """
    resident = (
        db.query(models.Resident)
        .filter(models.Resident.user_id == current_user.id)
        .first()
    )
    if not resident:
        raise HTTPException(status_code=404, detail="No resident profile for this user")
    return resident


@router.get(
    "/{resident_id}",
    response_model=schemas.ResidentOut,
    summary="Get a resident by ID",
    description=(
        "Retrieve a single resident profile. "
        "Admins can access any profile; residents can only access their own."
    ),
)
# PUBLIC_INTERFACE
def get_resident(
    resident_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Retrieve a resident profile by ID.

    Admins see all fields; residents can only view their own profile.
    """
    resident = _get_resident_or_404(resident_id, db)
    # Non-admin users may only view their own profile
    if current_user.role != "admin" and resident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return resident


@router.put(
    "/{resident_id}",
    response_model=schemas.ResidentOut,
    summary="Update a resident profile",
    description=(
        "Update a resident profile. "
        "Admins can update any profile; residents can only update their own."
    ),
)
# PUBLIC_INTERFACE
def update_resident(
    resident_id: int,
    resident_in: schemas.ResidentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Update an existing resident profile.

    Only admins may set `is_active` or change `building_id`.
    """
    resident = _get_resident_or_404(resident_id, db)
    if current_user.role != "admin" and resident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    update_data = resident_in.model_dump(exclude_unset=True)

    # Residents cannot deactivate themselves or change building via this route
    if current_user.role != "admin":
        update_data.pop("is_active", None)

    for field, value in update_data.items():
        setattr(resident, field, value)

    db.commit()
    db.refresh(resident)
    return resident


@router.delete(
    "/{resident_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resident profile (admin only)",
    description="Permanently delete a resident profile. Admin access required.",
)
# PUBLIC_INTERFACE
def delete_resident(
    resident_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Delete a resident profile by ID.

    Admin only. This does NOT delete the linked user account.
    """
    resident = _get_resident_or_404(resident_id, db)
    db.delete(resident)
    db.commit()


@router.get(
    "/{resident_id}/privacy",
    response_model=schemas.PrivacySettingsOut,
    summary="Get privacy settings for a resident",
    description="Return the privacy settings of a resident profile.",
)
# PUBLIC_INTERFACE
def get_privacy_settings(
    resident_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Retrieve privacy settings for a resident."""
    resident = _get_resident_or_404(resident_id, db)
    if current_user.role != "admin" and resident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    if not resident.privacy_settings:
        raise HTTPException(status_code=404, detail="Privacy settings not found")
    return resident.privacy_settings


@router.put(
    "/{resident_id}/privacy",
    response_model=schemas.PrivacySettingsOut,
    summary="Update privacy settings for a resident",
    description=(
        "Update visibility flags for a resident's profile fields. "
        "Residents may update their own; admins can update any."
    ),
)
# PUBLIC_INTERFACE
def update_privacy_settings(
    resident_id: int,
    privacy_in: schemas.PrivacySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Update privacy settings for a resident profile.

    Controls which fields (phone, email, unit, photo) are visible in the directory.
    """
    resident = _get_resident_or_404(resident_id, db)
    if current_user.role != "admin" and resident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    privacy = resident.privacy_settings
    if not privacy:
        # Create if missing
        privacy = models.PrivacySettings(resident_id=resident_id)
        db.add(privacy)
        db.flush()

    update_data = privacy_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(privacy, field, value)

    db.commit()
    db.refresh(privacy)
    return privacy
