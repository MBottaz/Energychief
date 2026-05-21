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
