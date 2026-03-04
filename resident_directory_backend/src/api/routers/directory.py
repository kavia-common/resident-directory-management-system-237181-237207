"""
Directory router providing the public-facing searchable resident directory.
Contact fields are filtered based on each resident's privacy settings.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/directory", tags=["Directory"])


def _apply_privacy(resident: models.Resident) -> schemas.DirectoryResidentOut:
    """
    Build a DirectoryResidentOut from a Resident ORM object,
    masking fields according to privacy settings.
    """
    privacy = resident.privacy_settings
    building_name = resident.building.name if resident.building else None

    return schemas.DirectoryResidentOut(
        id=resident.id,
        first_name=resident.first_name,
        last_name=resident.last_name,
        unit_number=resident.unit_number if (not privacy or privacy.show_unit) else None,
        phone=resident.phone if (not privacy or privacy.show_phone) else None,
        email=resident.email if (not privacy or privacy.show_email) else None,
        photo_url=resident.photo_url if (not privacy or privacy.show_photo) else None,
        building_id=resident.building_id,
        building_name=building_name,
    )


@router.get(
    "/",
    response_model=List[schemas.DirectoryResidentOut],
    summary="Search the public resident directory",
    description=(
        "Return a list of active residents with contact fields filtered by each "
        "resident's privacy settings. Supports search by name, unit, or building."
    ),
)
# PUBLIC_INTERFACE
def search_directory(
    search: Optional[str] = Query(
        None, description="Search term matched against first/last name or unit number"
    ),
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Search the resident directory.

    - **search**: partial match on first name, last name, or unit number
    - **building_id**: filter to a specific building
    - **skip** / **limit**: pagination

    Returns privacy-filtered resident entries. Authentication required.
    """
    query = db.query(models.Resident).filter(models.Resident.is_active == True)  # noqa: E712

    if building_id is not None:
        query = query.filter(models.Resident.building_id == building_id)

    if search:
        term = f"%{search}%"
        query = query.filter(
            models.Resident.first_name.ilike(term)
            | models.Resident.last_name.ilike(term)
            | models.Resident.unit_number.ilike(term)
        )

    residents = query.offset(skip).limit(limit).all()
    return [_apply_privacy(r) for r in residents]
