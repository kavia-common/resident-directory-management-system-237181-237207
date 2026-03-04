"""
Buildings router providing CRUD endpoints for building/complex management.
Read access is open to authenticated users; write access requires admin role.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/buildings", tags=["Buildings"])


def _get_building_or_404(building_id: int, db: Session) -> models.Building:
    """Fetch a building by ID or raise 404."""
    building = db.query(models.Building).filter(models.Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get(
    "/",
    response_model=List[schemas.BuildingOut],
    summary="List all buildings",
    description="Retrieve all buildings/complexes. Authentication required.",
)
# PUBLIC_INTERFACE
def list_buildings(
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.get_current_active_user),
):
    """Return a list of all buildings."""
    return db.query(models.Building).all()


@router.post(
    "/",
    response_model=schemas.BuildingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a building (admin only)",
    description="Create a new building or complex. Admin access required.",
)
# PUBLIC_INTERFACE
def create_building(
    building_in: schemas.BuildingCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Create a new building record.

    Admin only.
    """
    building = models.Building(**building_in.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get(
    "/{building_id}",
    response_model=schemas.BuildingOut,
    summary="Get a building by ID",
    description="Retrieve details for a specific building. Authentication required.",
)
# PUBLIC_INTERFACE
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.get_current_active_user),
):
    """Return a single building by its ID."""
    return _get_building_or_404(building_id, db)


@router.put(
    "/{building_id}",
    response_model=schemas.BuildingOut,
    summary="Update a building (admin only)",
    description="Update building details. Admin access required.",
)
# PUBLIC_INTERFACE
def update_building(
    building_id: int,
    building_in: schemas.BuildingUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Update a building record.

    Admin only. Only the fields provided in the request body are updated.
    """
    building = _get_building_or_404(building_id, db)
    update_data = building_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(building, field, value)
    db.commit()
    db.refresh(building)
    return building


@router.delete(
    "/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a building (admin only)",
    description="Permanently delete a building record. Admin access required.",
)
# PUBLIC_INTERFACE
def delete_building(
    building_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Delete a building by ID.

    Admin only. Associated residents will have their building_id set to NULL.
    """
    building = _get_building_or_404(building_id, db)
    db.delete(building)
    db.commit()
