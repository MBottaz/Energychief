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
from shared.models import Rec, RecCabina, User, Meter, EnergyReading, WebhookEvent


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              USERS                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


def upsert_user_by_telegram(
    telegram_id: int,
    first_name: str,
    rec_id: int | None = None,
    pod: str | None = None,
) -> User:
    """Create or update a user. Returns the User instance."""
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.first_name = first_name
            if rec_id is not None:
                user.rec_id = rec_id
            if pod is not None:
                user.pod = pod
        else:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                rec_id=rec_id,
                pod=pod,
            )
            session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_user_by_telegram_id(telegram_id: int) -> User | None:
    with SessionLocal() as session:
        return session.query(User).filter_by(telegram_id=telegram_id).first()



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
    """Seed RECs and their cabine primarie from a CSV file.

    The CSV may contain multiple rows for the same REC (same name) 
    to associate it with multiple cabine primarie. Each row's 
    pod_prefix is added as a cabina_code in rec_cabine.
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Seed file {csv_path} not found.")
        return 0

    new_recs = 0
    new_cabine = 0
    with SessionLocal() as session:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lat_str = row.get("latitude", "").strip()
                lon_str = row.get("longitude", "").strip()
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None
                name = row["name"].strip()
                cabina_code = row.get("pod_prefix", "").strip()

                # Upsert REC by name
                rec = session.query(Rec).filter_by(name=name).first()
                if not rec:
                    rec = Rec(name=name, latitude=lat, longitude=lon)
                    session.add(rec)
                    session.flush()  # get rec_id assigned
                    new_recs += 1

                # Add cabina association if not already present
                if cabina_code:
                    exists = session.query(RecCabina).filter_by(
                        rec_id=rec.rec_id, cabina_code=cabina_code
                    ).first()
                    if not exists:
                        session.add(RecCabina(rec_id=rec.rec_id, cabina_code=cabina_code))
                        new_cabine += 1

        session.commit()
    print(f"Seeded {new_recs} new RECs, {new_cabine} new cabine associations.")
    return new_recs + new_cabine


def get_all_recs() -> list[Rec]:
    with SessionLocal() as session:
        return session.query(Rec).all()


def get_recs_by_cabina(cod_ac: str) -> list[Rec]:
    """Returns RECs linked to the given cabina primaria code."""
    with SessionLocal() as session:
        return (
            session.query(Rec)
            .join(RecCabina)
            .filter(RecCabina.cabina_code == cod_ac)
            .all()
        )


def get_users_in_rec(rec_id: int) -> list[User]:
    """Returns all users belonging to a given REC."""
    with SessionLocal() as session:
        return (
            session.query(User)
            .filter_by(rec_id=rec_id)
            .all()
        )


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                     METERS & READINGS (atomic)                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


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


def save_meter_reading(
    meter_id: str,
    owner_user_id: int | None,
    power_kw: float,
    timestamp: str,
    producer: str | None = None,
    model: str | None = None,
    site_name: str | None = None,
    *,
    delivery_id: str | None = None,
    event_type: str | None = None,
    raw_payload: str | None = None,
) -> None:
    """
    Atomically upsert a meter, save a reading, and optionally log a webhook event.

    All three operations happen in a single transaction, so a partial failure
    cannot leave the database inconsistent.

    Pass *delivery_id*, *event_type*, *raw_payload* when processing a webhook
    event from Enode. Omit them when called from the polling loop.
    """
    with SessionLocal() as session:
        # ── upsert meter ──
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

        # ── save reading ──
        reading = (
            session.query(EnergyReading)
            .filter_by(meter_id=meter_id, timestamp=timestamp)
            .first()
        )
        if reading:
            reading.power_kw = power_kw
        else:
            reading = EnergyReading(
                meter_id=meter_id, timestamp=timestamp, power_kw=power_kw
            )
            session.add(reading)

        # ── optionally log webhook event ──
        if raw_payload is not None:
            event = WebhookEvent(
                delivery_id=delivery_id,
                event_type=event_type,
                meter_id=meter_id,
                payload=raw_payload,
            )
            session.add(event)

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