import csv
import os
import sqlite3
import pathlib
from config import DB_PATH


def get_connection(db_path: pathlib.Path = DB_PATH) -> sqlite3.Connection:
    """
    Opens and returns a SQLite connection.
    Accepts an optional db_path so Phase 9 can pass a per-CER path.
    row_factory lets us access columns by name (row["heating"]) instead
    of index (row[0]).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: pathlib.Path = DB_PATH) -> None:
    """
    Creates all tables if they don't exist yet.
    Safe to call every time the bot starts — CREATE TABLE IF NOT EXISTS
    is idempotent.
    """
    with get_connection(db_path) as conn:
        # 1. Existing users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER UNIQUE,
                first_name      TEXT,
                heating         TEXT,
                electricity_rate REAL,
                gas_rate        REAL,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        # 2. New recs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recs (
                rec_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                latitude    REAL,
                longitude   REAL,
                pod_prefix  TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        # 3. New meters table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meters (
                meter_id        TEXT PRIMARY KEY,
                owner_user_id   INTEGER REFERENCES users(telegram_id),
                producer        TEXT,
                model           TEXT,
                linked_at       TEXT DEFAULT (datetime('now'))
            )
        """)

        # 4. New energy_readings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS energy_readings (
                reading_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                meter_id        TEXT REFERENCES meters(meter_id),
                timestamp       TEXT NOT NULL,
                power_kw        REAL,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        # 5. Alter existing tables
        # Using a loop with try/except as SQLite doesn't support IF NOT EXISTS for columns
        alterations = [
            ("users", "rec_id", "INTEGER REFERENCES recs(rec_id)"),
            ("users", "threshold_kwh", "REAL DEFAULT 2.0"),
            ("users", "notification_interval_hours", "INTEGER DEFAULT 4"),
            ("users", "last_notified_at", "TEXT"),
            ("recs", "pod_prefix", "TEXT"),
        ]

        for table_name, column_name, column_def in alterations:
            try:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            except sqlite3.OperationalError:
                # Column already exists
                pass

        conn.commit()


def upsert_user_by_telegram(
    telegram_id: int,
    first_name: str,
    heating: str,
    electricity_rate: float,
    gas_rate: float,
    db_path: pathlib.Path = DB_PATH,
) -> None:
    """
    Inserts a new user row or updates it if telegram_id already exists.
    """
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO users (telegram_id, first_name, heating, electricity_rate, gas_rate, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                first_name       = excluded.first_name,
                heating          = excluded.heating,
                electricity_rate = excluded.electricity_rate,
                gas_rate         = excluded.gas_rate,
                updated_at       = excluded.updated_at
        """, (telegram_id, first_name, heating, electricity_rate, gas_rate))
        conn.commit()


def get_user_by_telegram_id(
    telegram_id: int,
    db_path: pathlib.Path = DB_PATH,
) -> sqlite3.Row | None:
    """
    Returns the user row for telegram_id, or None if not found.
    """
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_user_id(
    user_id: int,
    db_path: pathlib.Path = DB_PATH,
) -> sqlite3.Row | None:
    """
    Returns the user row for user_id, or None if not found.
    """
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()


def get_all_recs(db_path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    """Returns all rows from recs."""
    with get_connection(db_path) as conn:
        return conn.execute("SELECT * FROM recs").fetchall()


def get_users_in_rec(rec_id: int, db_path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    """Returns all users with a given rec_id."""
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT telegram_id, threshold_kwh, notification_interval_hours, last_notified_at "
            "FROM users WHERE rec_id = ?",
            (rec_id,),
        ).fetchall()


def get_meters_for_rec(rec_id: int, db_path: pathlib.Path = DB_PATH) -> list[str]:
    """Returns a list of meter_id values for all users in the given REC."""
    with get_connection(db_path) as conn:
        return [
            row["meter_id"]
            for row in conn.execute(
                """
                SELECT m.meter_id
                FROM meters m
                JOIN users u ON m.owner_user_id = u.telegram_id
                WHERE u.rec_id = ?
                """,
                (rec_id,),
            )
        ]


def save_energy_reading(
    meter_id: str, timestamp: str, power_kw: float, db_path: pathlib.Path = DB_PATH
) -> None:
    """Inserts a row into energy_readings."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO energy_readings (meter_id, timestamp, power_kw) VALUES (?, ?, ?)",
            (meter_id, timestamp, power_kw),
        )
        conn.commit()


def update_last_notified(telegram_id: int, db_path: pathlib.Path = DB_PATH) -> None:
    """Sets last_notified_at = datetime('now') for the given user."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE users SET last_notified_at = datetime('now') WHERE telegram_id = ?",
            (telegram_id,),
        )
        conn.commit()


def seed_recs_from_csv(csv_path: str, db_path: pathlib.Path = DB_PATH) -> int:
    """
    Reads a CSV file and populates the recs table.
    Returns the number of new rows inserted.
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Seed file {csv_path} not found.")
        return 0

    new_count = 0
    with get_connection(db_path) as conn:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle empty strings for numeric fields
                lat_str = row.get('latitude', '').strip()
                lon_str = row.get('longitude', '').strip()
                lat = float(lat_str) if lat_str else None
                lon = float(lon_str) if lon_str else None
                name = row['name'].strip()
                pod_prefix = row.get('pod_prefix', '').strip()

                try:
                    conn.execute(
                        """
                        INSERT INTO recs (name, latitude, longitude, pod_prefix)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(name) DO NOTHING
                        """,
                        (name, lat, lon, pod_prefix),
                    )
                    if conn.total_changes > 0:
                        new_count += 1
                except Exception as e:
                    print(f"Error seeding REC {name}: {e}")
        conn.commit()
    return new_count


def get_latest_power_per_meter(rec_id: int, db_path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    """For each meter belonging to users in the given REC, returns the most recent energy_readings row."""
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT er.meter_id, er.power_kw, er.timestamp
            FROM energy_readings er
            JOIN meters m ON er.meter_id = m.meter_id
            JOIN users u ON m.owner_user_id = u.telegram_id
            WHERE u.rec_id = ?
            AND er.reading_id = (
                SELECT MAX(reading_id) FROM energy_readings WHERE meter_id = er.meter_id
            )
            """,
            (rec_id,),
        ).fetchall()
