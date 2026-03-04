"""
Pydantic v2 schemas for request validation and response serialization.
All public-facing models are documented with Field descriptions.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# Token / Auth schemas
# =============================================================================

class Token(BaseModel):
    """JWT access token response."""

    access_token: str = Field(..., description="JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token type, always 'bearer'")


class TokenData(BaseModel):
    """Internal token payload parsed from JWT."""

    username: Optional[str] = None
    role: Optional[str] = None


# =============================================================================
# Building schemas
# =============================================================================

class BuildingBase(BaseModel):
    """Shared building fields."""

    name: str = Field(..., max_length=255, description="Name of the building or complex")
    address: Optional[str] = Field(None, description="Street address")
    description: Optional[str] = Field(None, description="Optional description")


class BuildingCreate(BuildingBase):
    """Schema for creating a building (admin only)."""
    pass


class BuildingUpdate(BaseModel):
    """Schema for updating a building (all fields optional)."""

    name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    description: Optional[str] = None


class BuildingOut(BuildingBase):
    """Building response schema."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# User / Auth schemas
# =============================================================================

class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr = Field(..., description="User email address (unique)")
    username: str = Field(..., max_length=100, description="Unique username")


class UserCreate(UserBase):
    """Schema for registering a new user."""

    password: str = Field(..., min_length=6, description="Plain-text password (min 6 chars)")
    role: str = Field(default="resident", description="Role: 'admin' or 'resident'")


class UserUpdate(BaseModel):
    """Schema for updating user fields."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserOut(UserBase):
    """Public user response (no password)."""

    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Privacy Settings schemas
# =============================================================================

class PrivacySettingsBase(BaseModel):
    """Shared privacy setting flags."""

    show_phone: bool = Field(default=True, description="Show phone in directory")
    show_email: bool = Field(default=True, description="Show email in directory")
    show_unit: bool = Field(default=True, description="Show unit number in directory")
    show_photo: bool = Field(default=True, description="Show photo in directory")


class PrivacySettingsUpdate(BaseModel):
    """Schema for partial privacy settings update."""

    show_phone: Optional[bool] = None
    show_email: Optional[bool] = None
    show_unit: Optional[bool] = None
    show_photo: Optional[bool] = None


class PrivacySettingsOut(PrivacySettingsBase):
    """Privacy settings response."""

    id: int
    resident_id: int

    model_config = {"from_attributes": True}


# =============================================================================
# Resident schemas
# =============================================================================

class ResidentBase(BaseModel):
    """Shared resident profile fields."""

    first_name: str = Field(..., max_length=100, description="First name")
    last_name: str = Field(..., max_length=100, description="Last name")
    unit_number: Optional[str] = Field(None, max_length=50, description="Unit/apartment number")
    phone: Optional[str] = Field(None, max_length=30, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    photo_url: Optional[str] = Field(None, description="URL to profile photo")
    building_id: Optional[int] = Field(None, description="Associated building ID")
    move_in_date: Optional[date] = Field(None, description="Move-in date")
    move_out_date: Optional[date] = Field(None, description="Move-out date")


class ResidentCreate(ResidentBase):
    """Schema for creating a resident profile."""

    user_id: Optional[int] = Field(None, description="Linked user account ID")


class ResidentUpdate(BaseModel):
    """Schema for partial resident profile update."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    unit_number: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    photo_url: Optional[str] = None
    building_id: Optional[int] = None
    move_in_date: Optional[date] = None
    move_out_date: Optional[date] = None
    is_active: Optional[bool] = None


class ResidentOut(ResidentBase):
    """Full resident response (for admins and self)."""

    id: int
    user_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    privacy_settings: Optional[PrivacySettingsOut] = None

    model_config = {"from_attributes": True}


class DirectoryResidentOut(BaseModel):
    """
    Public directory view of a resident.
    Fields are conditionally included based on privacy settings.
    """

    id: int = Field(..., description="Resident ID")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    unit_number: Optional[str] = Field(None, description="Unit number (if visible)")
    phone: Optional[str] = Field(None, description="Phone (if visible)")
    email: Optional[str] = Field(None, description="Email (if visible)")
    photo_url: Optional[str] = Field(None, description="Photo URL (if visible)")
    building_id: Optional[int] = Field(None, description="Building ID")
    building_name: Optional[str] = Field(None, description="Building name")

    model_config = {"from_attributes": True}


# =============================================================================
# Announcement schemas
# =============================================================================

class AnnouncementBase(BaseModel):
    """Shared announcement fields."""

    title: str = Field(..., max_length=255, description="Announcement title")
    body: str = Field(..., description="Announcement body text")
    building_id: Optional[int] = Field(
        None, description="Target building; NULL means all buildings"
    )
    is_pinned: bool = Field(default=False, description="Whether to pin this announcement")


class AnnouncementCreate(AnnouncementBase):
    """Schema for creating an announcement (admin only)."""
    pass


class AnnouncementUpdate(BaseModel):
    """Schema for partial announcement update."""

    title: Optional[str] = Field(None, max_length=255)
    body: Optional[str] = None
    building_id: Optional[int] = None
    is_pinned: Optional[bool] = None


class AnnouncementOut(AnnouncementBase):
    """Announcement response."""

    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Message schemas
# =============================================================================

class MessageCreate(BaseModel):
    """Schema for sending a direct message."""

    recipient_id: int = Field(..., description="Recipient user ID")
    subject: Optional[str] = Field(None, max_length=255, description="Message subject")
    body: str = Field(..., description="Message body text")


class MessageOut(BaseModel):
    """Message response."""

    id: int
    sender_id: int
    recipient_id: int
    subject: Optional[str]
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Admin user management schema
# =============================================================================

class AdminUserOut(UserOut):
    """Extended user info returned to admins."""

    updated_at: datetime

    model_config = {"from_attributes": True}
