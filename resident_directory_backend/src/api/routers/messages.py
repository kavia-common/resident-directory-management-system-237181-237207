"""
Messages router providing direct messaging between residents.
Users can only access their own sent/received messages.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api import auth, models, schemas
from src.api.database import get_db

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get(
    "/inbox",
    response_model=List[schemas.MessageOut],
    summary="Get inbox (received messages)",
    description="Return all messages received by the authenticated user.",
)
# PUBLIC_INTERFACE
def get_inbox(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Return received messages for the current user, newest first."""
    return (
        db.query(models.Message)
        .filter(models.Message.recipient_id == current_user.id)
        .order_by(models.Message.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/sent",
    response_model=List[schemas.MessageOut],
    summary="Get sent messages",
    description="Return all messages sent by the authenticated user.",
)
# PUBLIC_INTERFACE
def get_sent(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """Return sent messages for the current user, newest first."""
    return (
        db.query(models.Message)
        .filter(models.Message.sender_id == current_user.id)
        .order_by(models.Message.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/",
    response_model=schemas.MessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Send a direct message",
    description="Send a direct message to another user. Authentication required.",
)
# PUBLIC_INTERFACE
def send_message(
    message_in: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Send a direct message to another user.

    - **recipient_id**: target user's ID
    - **subject**: optional subject line
    - **body**: message content
    """
    # Verify recipient exists
    recipient = db.query(models.User).filter(models.User.id == message_in.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if message_in.recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send a message to yourself")

    message = models.Message(
        sender_id=current_user.id,
        recipient_id=message_in.recipient_id,
        subject=message_in.subject,
        body=message_in.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get(
    "/{message_id}",
    response_model=schemas.MessageOut,
    summary="Get a message by ID",
    description="Retrieve a specific message. Only sender or recipient may access it.",
)
# PUBLIC_INTERFACE
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Retrieve a specific message by ID.

    Marks the message as read if the current user is the recipient.
    """
    message = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Only sender or recipient may access the message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    # Mark as read when recipient views it
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)

    return message


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a message",
    description="Delete a message. Only the sender or an admin can delete it.",
)
# PUBLIC_INTERFACE
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user),
):
    """
    Delete a message by ID.

    Only the sender or an admin may delete a message.
    """
    message = db.query(models.Message).filter(models.Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if current_user.role != "admin" and message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    db.delete(message)
    db.commit()
