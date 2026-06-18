"""
Database layer for Energychief — SQLAlchemy edition.

All database access goes through this module. Functions mirror the
original sqlite3 interface so callers need minimal changes.
"""

import csv
import math
import os
import pathlib

from sqlalchemy import text
from shared.engine import SessionLocal
from shared.models import Rec, User, Meter, EnergyReading, WebhookEvent


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              USERS                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def upsert_user_by_telegram(
    telegram_id: int,
    first_name: str,
    rec_id: int | None = None,
) -> User:
    """Create or update a user. Returns the User instance."""
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.first_name = first_name
            if rec_id is not None:
                user.rec_id = rec_id
        else:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                rec_id=rec_id,
            )
            session.add(user)
        session.commit()
        # Refresh to get generated fields (user_id, etc.)
        session.refresh(user)
        return user


def get_user_by_telegram_id(telegram_id: int) -> User | None:
    with SessionLocal() as session:
        return session.query(User).filter_by(telegram_id=telegram_id).first()


def get_user_by_user_id(user_id: int) -> User | None:
    with SessionLocal() as session:
        return session.query(User).filter_by(user_id=user_id).first()


def update_last_notified(telegram_id: int) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            from datetime import datetime
            user.last_notified_at = datetime.utcnow().isoformat()
            session.commit()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                               RECs                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def seed_recs_from_csv(csv_path: str) -> int:
    if not os.path.exists(csv_path):
        print(f"Warning: Seed file {csv_path} not found.")
        return 0

    new_count = 0
    with SessionLocal() as session:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lat_str = row.get("latitude", "").strip()
                lon_str = row.get("longitude", "").strip()
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None
                name = row["name"].strip()
                pod_prefix = row.get("pod_prefix", "").strip()

                existing = session.query(Rec).filter_by(name=name).first()
                if existing:
                    continue

                rec = Rec(name=name, latitude=lat, longitude=lon, pod_prefix=pod_prefix)
                session.add(rec)
                new_count += 1
        session.commit()
    return new_count


def get_all_recs() -> list[Rec]:
    with SessionLocal() as session:
        return session.query(Rec).all()


def get_users_in_rec(rec_id: int) -> list[User]:
    """Returns all users belonging to a given REC."""
    with SessionLocal() as session:
        return (
            session.query(User)
            .filter_by(rec_id=rec_id)
            .all()
        )


def get_meters_for_rec(rec_id: int) -> list[str]:
    """Returns a list of meter_id values for all users in the given REC."""
    with SessionLocal() as session:
        rows = (
            session.query(Meter.meter_id)
            .join(User, Meter.owner_user_id == User.user_id)
            .filter(User.rec_id == rec_id)
            .all()
        )
        return [row[0] for row in rows]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        WEBHOOK EVENTS LOG                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def log_webhook_event(
    delivery_id: str | None,
    event_type: str | None,
    meter_id: str | None,
    payload: str,
) -> None:
    with SessionLocal() as session:
        event = WebhookEvent(
            delivery_id=delivery_id,
            event_type=event_type,
            meter_id=meter_id,
            payload=payload,
        )
        session.add(event)
        session.commit()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          METERS & READINGS                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def upsert_meter(
    meter_id: str,
    owner_user_id: int | None,
    producer: str | None = None,
    model: str | None = None,
    site_name: str | None = None,
) -> None:
    with SessionLocal() as session:
        meter = session.query(Meter).filter_by(meter_id=meter_id).first()
        if meter:
            if owner_user_id is not None:
                meter.owner_user_id = owner_user_id
            if producer is not None:
                meter.producer = producer
            if model is not None:
                meter.model = model
            if site_name is not None:
                meter.site_name = site_name
        else:
            meter = Meter(
                meter_id=meter_id,
                owner_user_id=owner_user_id,
                producer=producer,
                model=model,
                site_name=site_name,
            )
            session.add(meter)
        session.commit()


def get_meters_for_user(user_id: int) -> list[Meter]:
    """Returns all meters owned by the given user."""
    with SessionLocal() as session:
        return session.query(Meter).filter_by(owner_user_id=user_id).all()


def get_latest_reading_for_meter(meter_id: str) -> EnergyReading | None:
    """
    Returns the most recent reading with a valid (non-NaN) power value.
    Skips readings where power_kw is NaN or None.
    """
    with SessionLocal() as session:
        readings = (
            session.query(EnergyReading)
            .filter_by(meter_id=meter_id)
            .order_by(EnergyReading.timestamp.desc())
            .limit(20)
            .all()
        )
        for r in readings:
            if r.power_kw is not None and not math.isnan(r.power_kw):
                return r
        return None


def save_energy_reading(meter_id: str, timestamp: str, power_kw: float) -> None:
    with SessionLocal() as session:
        reading = (
            session.query(EnergyReading)
            .filter_by(meter_id=meter_id, timestamp=timestamp)
            .first()
        )
        if reading:
            reading.power_kw = power_kw
        else:
            reading = EnergyReading(meter_id=meter_id, timestamp=timestamp, power_kw=power_kw)
            session.add(reading)
        session.commit()


def get_latest_power_per_meter(rec_id: int) -> list[dict]:
    """For each meter in the REC, returns the most recent reading.

    Returns a list of dicts with keys: meter_id, power_kw, timestamp.
    """
    with SessionLocal() as session:
        rows = session.execute(
            text("""
                SELECT er.meter_id, er.power_kw, er.timestamp
                FROM energy_readings er
                JOIN meters m ON er.meter_id = m.meter_id
                JOIN users u ON m.owner_user_id = u.user_id
                WHERE u.rec_id = :rec_id
                AND er.timestamp = (
                    SELECT MAX(timestamp) FROM energy_readings WHERE meter_id = er.meter_id
                )
            """),
            {"rec_id": rec_id},
        ).mappings().all()
        return [dict(r) for r in rows]