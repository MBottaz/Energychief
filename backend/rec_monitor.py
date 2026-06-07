from backend.enode_api import get_all_meters
from shared.database import save_energy_reading, upsert_meter

async def collect_and_store_readings() -> None:
    """
    Fetches all meters from Enode and saves the latest energyState 
    to the database.
    """
    meters = await get_all_meters()
    
    for meter in meters:
        try:
            is_reachable = meter.get("isReachable", False)
            energy_state = meter.get("energyState")

            if is_reachable and energy_state is not None:
                meter_id = meter["id"]
                power_kw = energy_state["power"]
                timestamp = energy_state["lastUpdated"]

                # Upsert meter into local meters table so REC queries can JOIN
                enode_user_id = meter.get("userId")
                owner_user_id = int(enode_user_id) if enode_user_id and enode_user_id.isdigit() else None
                info = meter.get("information", {}) or {}
                upsert_meter(
                    meter_id=meter_id,
                    owner_user_id=owner_user_id,
                    producer=info.get("brand"),
                    model=info.get("model"),
                )

                save_energy_reading(meter_id, timestamp, power_kw)
        except Exception as e:
            meter_id = meter.get("id", "unknown")
            print(f"Failed to save reading for meter {meter_id}: {e}")
