import aiosqlite
from typing import Any, Optional, List, Dict
from datetime import datetime
from src.energychief.db.connection import get_db

async def get_cer_by_prefix(pod_prefix: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a CER by its POD prefix.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM cer WHERE pod_prefix = ?", (pod_prefix,)
        ) as cursor:
            return await cursor.fetchone()

async def create_cer(name: str, pod_prefix: str) -> int:
    """
    Creates a new CER. Returns the new ID.
    """
    async for db in get_db():
        cursor = await db.execute(
            "INSERT INTO cer (name, pod_prefix) VALUES (?, ?)", (name, pod_prefix)
        )
        cer_id = cursor.lastrowid
        await db.commit()
        return cer_id

async def create_member(
    telegram_id: int, 
    telegram_username: Optional[str], 
    cer_id: Optional[int], 
    role: str, 
    pod: str
) -> int:
    """
    Creates a new member. Returns the new ID.
    """
    async for db in get_db():
        cursor = await db.execute(
            """
            INSERT INTO member (telegram_id, telegram_username, cer_id, role, pod)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, telegram_username, cer_id, role, pod),
        )
        member_id = cursor.lastrowid
        await db.commit()
        return member_id

async def get_member_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a member by their Telegram ID.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM member WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_active_members_by_cer(cer_id: int) -> List[Dict[str, Any]]:
    """
    Retrieves all active members of a CER.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM member WHERE cer_id = ? AND is_active = 1", (cer_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def create_prosumer_plant(
    member_id: int,
    enode_user_id: str,
    latitude: float,
    longitude: float,
    enode_meter_id: Optional[str] = None,
    enode_inverter_id: Optional[str] = None,
    enode_battery_id: Optional[str] = None,
    capacity_kwp: Optional[float] = None,
    export_threshold_kw: float = 1.0
) -> int:
    """
    Creates a prosumer plant configuration. Returns the new ID.
    """
    async for db in get_db():
        cursor = await db.execute(
            """
            INSERT INTO prosumer_plant (
                member_id, enode_user_id, enode_meter_id, enode_inverter_id, 
                enode_battery_id, latitude, longitude, capacity_kwp, export_threshold_kw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                member_id, enode_user_id, enode_meter_id, enode_inverter_id,
                enode_battery_id, latitude, longitude, capacity_kwp, export_threshold_kw
            ),
        )
        plant_id = cursor.lastrowid
        await db.commit()
        return plant_id

async def get_prosumer_plant_by_member_id(member_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves a prosumer plant by member ID.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM prosumer_plant WHERE member_id = ?", (member_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_all_prosumer_plants() -> List[Dict[str, Any]]:
    """
    Retrieves all active prosumer plants with their member information.
    """
    async for db in get_db():
        async with db.execute(
            """
            SELECT p.*, m.telegram_id, m.telegram_username, m.cer_id, c.name as cer_name
            FROM prosumer_plant p
            JOIN member m ON p.member_id = m.id
            JOIN cer c ON m.cer_id = c.id
            WHERE m.is_active = 1
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def save_reading(plant_id: int, reading_data: Dict[str, Any]):
    """
    Saves an energy reading.
    """
    async for db in get_db():
        await db.execute(
            """
            INSERT INTO energy_reading (
                prosumer_plant_id, timestamp, grid_power_kw, 
                inverter_power_kw, battery_soc_pct, battery_power_kw
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                plant_id,
                reading_data["timestamp"],
                reading_data.get("grid_power_kw"),
                reading_data.get("inverter_power_kw"),
                reading_data.get("battery_soc_pct"),
                reading_data.get("battery_power_kw"),
            ),
        )
        await db.commit()

async def log_notification(
    cer_id: int, 
    plant_id: int, 
    notif_type: str, 
    grid_power_kw: float, 
    recipients_count: int
):
    """
    Logs a sent notification.
    """
    async for db in get_db():
        await db.execute(
            """
            INSERT INTO notification_log (cer_id, prosumer_plant_id, type, grid_power_kw, recipients_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cer_id, plant_id, notif_type, grid_power_kw, recipients_count),
        )
        await db.commit

async def update_prosumer_plant(plant_id: int, updates: Dict[str, Any]):
    """
    Updates prosumer plant configuration.
    """
    if not updates:
        return
    
    async for db in get_db():
        keys = [f"{k} = ?" for k in updates.keys()]
        values = list(updates.values())
        values.append(plant_id)
        query = f"UPDATE prosumer_plant SET {', '.join(keys)} WHERE id = ?"
        await db.execute(query, values)
        await db.commit()

async def get_notification_preferences(member_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves notification preferences for a member.
    """
    async for db in get_db():
        async with db.execute(
            "SELECT * FROM notification_preference WHERE member_id = ?", (member_id,)
        ) as cursor:
            return await cursor.fetchone()

async def create_notification_preference(member_id: int, **kwargs):
    """
    Creates notification preferences for a member.
    """
    async for db in get_db():
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        values.append(member_id)
        query = f"INSERT INTO notification_preference ({', '.join(keys)}, member_id) VALUES ({', '.join(['?']*len(keys))}, ?)"
        # Wait, the order in the SQL above was wrong. Corrected:
        query = f"INSERT INTO notification_preference ({', '.join(keys)}, member_id) VALUES ({', '.join(['?']*len(keys))}, ?)"
        # Let's fix it simply
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        query = f"INSERT INTO notification_preference ({cols}, member_id) VALUES ({placeholders}, ?)"
        await db.execute(query, list(kwargs.values()) + [member_id])
        await db.commit()

async def get_system_config(key: str) -> Optional[str]:
    """
    Gets a system configuration value.
    """
    async for db in get_db():
        async with db.execute("SELECT value FROM system_config WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else None

async def set_system_config(key: str, value: str):
    """
    Sets a system configuration value.
    """
    async for db in get_db():
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, value),
        )
        await db.commit()
