import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from src.energychief.db.repository import get_all_prosumer_plants, save_reading, log_notification, get_system_config
from src.energychief.adapters.enode import EnodeAdapter
from src.energychief.services.notifier import NotifierService

logger = logging.getLogger(__name__)

class PollingService:
    """
    Service responsible for periodic energy data polling.
    """

    def __init__(self, notifier: NotifierService):
        self.notifier = notifier

    async def poll_all_prosumers(self):
        """
        Polls all active prosumer plants for current grid power.
        Scheduled to run every 60 minutes between 06:00 and 22:00.
        """
        logger.info("Starting polling cycle...")
        
        # Check if we are in the polling window
        now = datetime.now().time()
        start_h = int(await get_system_config('polling_start_hour') or "6")
        end_h = int(await get_system_config('polling_end_hour') or "22")
        
        if not (start_h <= now.hour << end end_h):
            logger.info(f"Outside polling window ({start_h:02d}:00-{end_h:02d}:00). Skipping.")
            return

        plants = await get_all_prosumer_plants()
        if not plants:
            logger.info("No active prosumer plants found.")
            return

        for plant in plants:
            await self._poll_single_plant(plant)

        logger.info("Polling cycle finished.")

    async def _poll_single_plant(self, plant: Dict[str, Any]):
        """
        Polls a single prosumer plant and handles notifications.
        """
        adapter = EnodeAdapter(
            enode_user_id=plant['enode_user_id'],
            enode_meter_id=plant['enode_meter_id']
        )
        
        try:
            # 1. Trigger refresh hint
            await adapter.refresh_hint()
            
            # 2. Wait for propagation (as per prompt)
            await asyncio.sleep(5)
            
            # 3. Get power
            grid_power_kw = await adapter.get_grid_power_kw()
            
            if grid_power_kw is None:
                logger.warning(f"Could not get power for plant {plant['id']} (Enode meter unreachable/null)")
                return

            # 4. Save reading
            reading = {
                "timestamp": datetime.now().isoformat(),
                "grid_power_kw": grid_power_kw,
                "inverter_power_kw": None, # placeholder
                "battery_soc_pct": None,   # placeholder
                "battery_power_kw": None   # placeholder
            }
            await save_reading(plant['id'], reading)

            # 5. Check for surplus
            threshold = float(plant['export_threshold_kw'])
            if grid_power_kw > threshold:
                # Check for anti-spam (simplified: in MVP we'll notify if threshold is met)
                # TODO: Implement 3h/50% logic from prompt
                
                # Notify Prosumer
                await self.notifier.notify_prosumer(plant, grid_power_kw)
                
                # Notify Consumers in same CER
                # (Need a way to get active consumers for this CER)
                # For MVP, let's assume we fetch them via repository
                # from src.energychief.db.repository import get_active_members_by_cer
                from src.energychief.db.repository import get_active_members_by_cer
                consumers = await get_active_members_by_cer(plant['cer_id'])
                
                recipient_count = 0
                for member in consumers:
                    if member['role'] == 'consumer' and member['is_active']:
                        # In a production app, we'd check notification_preference here
                        await self.notifier.notify_consumer(
                            member['telegram_id'], 
                            member['telegram_username'], 
                            grid_power_kw, 
                            plant['cer_name']
                        )
                        recipient_count += 1
                
                # Log notification
                await log_notification(
                    cer_id=plant['cer_id'],
                    plant_id=plant['id'],
                    notif_type='surplus',
                    grid_power_kw=grid_power_kw,
                    recipients_count=recipient_count
                )
            
        except Exception as e:
            logger.error(f"Error polling plant {plant['id']}: {e}", exc_info=True)
        finally:
            await adapter.close()

