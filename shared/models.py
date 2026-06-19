"""
SQLAlchemy ORM models for Energychief.

Maps to the same schema as the original sqlite3 tables so the
first Alembic migration captures them exactly.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, String, Text, ForeignKey, PrimaryKeyConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Rec(Base):
    __tablename__ = "recs"

    rec_id    = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(String, nullable=False, unique=True)
    latitude  = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(String, default=_utcnow)

    users = relationship("User", back_populates="rec")
    cabine = relationship("RecCabina", back_populates="rec", cascade="all, delete-orphan", lazy="selectin")


class User(Base):
    __tablename__ = "users"

    user_id                  = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id              = Column(Integer, unique=True, nullable=True)
    first_name               = Column(String, nullable=True)
    pod                      = Column(String, nullable=True)
    rec_id                   = Column(Integer, ForeignKey("recs.rec_id"), nullable=True)
    threshold_kwh            = Column(Float, default=2.0)
    notification_interval_hours = Column(Integer, default=4)
    last_notified_at         = Column(String, nullable=True)
    created_at               = Column(String, default=_utcnow)
    updated_at               = Column(String, default=_utcnow, onupdate=_utcnow)

    rec    = relationship("Rec", back_populates="users")
    meters = relationship("Meter", back_populates="owner")


class Meter(Base):
    __tablename__ = "meters"

    meter_id            = Column(String, primary_key=True)
    owner_user_id       = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    producer            = Column(String, nullable=True)
    model               = Column(String, nullable=True)
    site_name           = Column(String, nullable=True)
    consumption_enabled = Column(Integer, default=1)
    production_enabled  = Column(Integer, default=1)
    linked_at           = Column(String, default=_utcnow)

    owner       = relationship("User", back_populates="meters")
    readings    = relationship("EnergyReading", back_populates="meter")


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    meter_id  = Column(String, ForeignKey("meters.meter_id"), primary_key=True)
    timestamp = Column(String, primary_key=True)
    power_kw  = Column(Float, nullable=True)
    created_at = Column(String, default=_utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("meter_id", "timestamp"),
    )

    meter = relationship("Meter", back_populates="readings")


class RecCabina(Base):
    """Many-to-many: a REC can span multiple cabine primarie."""
    __tablename__ = "rec_cabine"

    rec_id = Column(Integer, ForeignKey("recs.rec_id"), primary_key=True)
    cabina_code = Column(String(20), primary_key=True)

    rec = relationship("Rec", back_populates="cabine")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(String, nullable=True)
    event_type  = Column(String, nullable=True)
    meter_id    = Column(String, nullable=True)
    payload     = Column(Text, nullable=True)
    received_at = Column(String, default=_utcnow)