"""
Announcements router.
Admins create/update/delete announcements; all authenticated users can read them.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/announcements", tags=["Announcements"])


def _get_announcement_or_404(announcement_id: int, db: Session) -> models.Announcement:
    """Fetch an announcement by ID or raise 404."""
    announcement = (
        db.query(models.Announcement)
        .filter(models.Announcement.id == announcement_id)
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


@router.get(
    "/",
    response_model=List[schemas.AnnouncementOut],
    summary="List announcements",
    description=(
        "Retrieve announcements. Optionally filter by building. "
        "Pinned announcements appear first. Authentication required."
    ),
)
# PUBLIC_INTERFACE
def list_announcements(
    building_id: Optional[int] = Query(None, description="Filter by building (NULL = all)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    List announcements ordered by pinned status then newest first.

    Pass `building_id` to get announcements for a specific building
    (also includes global announcements with no building).
    """
    query = db.query(models.Announcement)

    if building_id is not None:
        query = query.filter(
            (models.Announcement.building_id == building_id)
            | (models.Announcement.building_id.is_(None))
        )

    query = query.order_by(
        models.Announcement.is_pinned.desc(),
        models.Announcement.created_at.desc(),
    )
    return query.offset(skip).limit(limit).all()


@router.post(
    "/",
    response_model=schemas.AnnouncementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an announcement (admin only)",
    description="Create a new announcement. Admin access required.",
)
# PUBLIC_INTERFACE
def create_announcement(
    announcement_in: schemas.AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Create a new announcement.

    Admin only. Set `building_id` to target a specific building,
    or leave NULL to target all buildings.
    """
    announcement = models.Announcement(
        **announcement_in.model_dump(),
        author_id=current_user.id,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get(
    "/{announcement_id}",
    response_model=schemas.AnnouncementOut,
    summary="Get an announcement by ID",
    description="Retrieve a single announcement. Authentication required.",
)
# PUBLIC_INTERFACE
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(auth.get_current_active_user),
):
    """Return a single announcement by its ID."""
    return _get_announcement_or_404(announcement_id, db)


@router.put(
    "/{announcement_id}",
    response_model=schemas.AnnouncementOut,
    summary="Update an announcement (admin only)",
    description="Update announcement fields. Admin access required.",
)
# PUBLIC_INTERFACE
def update_announcement(
    announcement_id: int,
    announcement_in: schemas.AnnouncementUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Update an announcement.

    Admin only. Only supplied fields are modified.
    """
    announcement = _get_announcement_or_404(announcement_id, db)
    update_data = announcement_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an announcement (admin only)",
    description="Permanently delete an announcement. Admin access required.",
)
# PUBLIC_INTERFACE
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """
    Delete an announcement by ID.

    Admin only.
    """
    announcement = _get_announcement_or_404(announcement_id, db)
    db.delete(announcement)
    db.commit()
