"""
SQLAlchemy ORM models for the Resident Directory Management System.
Each class maps to one table in the PostgreSQL database.
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.api.database import Base


class Building(Base):
    """Maps to the 'buildings' table."""

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    residents = relationship("Resident", back_populates="building")
    announcements = relationship("Announcement", back_populates="building")


class User(Base):
    """Maps to the 'users' table. Stores credentials and roles."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="resident")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    resident = relationship("Resident", back_populates="user", uselist=False)
    announcements = relationship("Announcement", back_populates="author")
    sent_messages = relationship(
        "Message", foreign_keys="Message.sender_id", back_populates="sender"
    )
    received_messages = relationship(
        "Message", foreign_keys="Message.recipient_id", back_populates="recipient"
    )


class Resident(Base):
    """Maps to the 'residents' table. Stores resident profile data."""

    __tablename__ = "residents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    unit_number = Column(String(50))
    phone = Column(String(30))
    email = Column(String(255))
    photo_url = Column(Text)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True)
    move_in_date = Column(Date)
    move_out_date = Column(Date)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="resident")
    building = relationship("Building", back_populates="residents")
    privacy_settings = relationship(
        "PrivacySettings", back_populates="resident", uselist=False
    )


class PrivacySettings(Base):
    """Maps to the 'privacy_settings' table. Controls directory field visibility."""

    __tablename__ = "privacy_settings"

    id = Column(Integer, primary_key=True, index=True)
    resident_id = Column(
        Integer, ForeignKey("residents.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    show_phone = Column(Boolean, nullable=False, default=True)
    show_email = Column(Boolean, nullable=False, default=True)
    show_unit = Column(Boolean, nullable=False, default=True)
    show_photo = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    resident = relationship("Resident", back_populates="privacy_settings")


class Announcement(Base):
    """Maps to the 'announcements' table. Admin-posted announcements."""

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="announcements")
    building = relationship("Building", back_populates="announcements")


class Message(Base):
    """Maps to the 'messages' table. Direct messages between residents."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(255))
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
