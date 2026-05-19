import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

logger = logging.getLogger(__name__)

class NotifierService:
    """
    Service to handle dispatching notifications to CER members.
    """

    def __init__(self, application: Application):
        self.application = application

    async def notify_prosumer(self, prosumer_plant: Dict[str, Any], grid_power_kw: float):
        """
        Sends a notification to the prosumer that they are exporting energy.
        """
        telegram_id = prosumer_plant['telegram_id']
        # In a real app, we'd use a template from messages.py
        # For now, let's just use a simple string for the logic test
        message = (
            f"⚡ Energia disponibile nella tua CER!\n"
            f"Stai immettendo {grid_power_kw:.2f} kW in rete.\n"
            f"È un buon momento per attivare elettrodomestici!"
        )
        try:
            await self.application.bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Notification sent to prosumer {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to notify prosumer {telegram_id}: {e}")

    async def notify_consumer(self, telegram_id: int, username: Optional[str], grid_power_kw: float, prosumer_name: str):
        """
        Sends a notification to a consumer about surplus energy.
        """
        name = username if username else f"User {telegram_id}"
        message = (
            f"⚡ Energia disponibile nella tua CER!\n"
            f"{prosumer_name} sta immettendo {grid_power_kw:.2f} kW in rete.\n"
            f"È un buon momento per attivare lavatrice, lavastoviglie o ricarica EV!"
        )
        try:
            await self.application.bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Notification sent to consumer {name}")
        except Exception as e:
            logger.error(f"Failed to notify consumer {name}: {e}")

    async def send_forecast(self, telegram_id: int, username: Optional[str], date_str: str, best_hours: List[Dict[str, Any]]):
        """
        Sends the daily solar forecast to a member.
        """
        name = username if username else f"User {telegram_id}"
        
        hours_str = ""
        for hour in best_hours:
            # hour['timestamp'] is a datetime object
            h_str = hour['timestamp'].strftime("%H:%M")
            hours_str += f"• {h_str} — ~{hour['power_kw']:.1f} kW\n"

        message = (
            f"☀️ Previsione solare per oggi ({date_str}):\n"
            f"{hours_str}\n"
            f"💡 Consiglio: programma gli elettrodomestici nelle fasce evidenziate."
        )
        
        try:
            await self.application.bot.send_message(chat_id=telegram_id, text=message)
            logger.info(f"Forecast sent to {name}")
        except Exception as e:
            logger.error(f"Failed to send forecast to {name}: {e}")

    async def notify_end_of_surplus(self, telegram_id: int):
        """
        Sends a brief message when surplus ends.
        """
        message = "ℹ️ L'eccesso di energia nella CER è terminato."
        try:
            await self.application.bot.send_message(chat_id=telegram_id, text=message)
        except Exception as e:
            logger.error(f"Failed to notify end of surplus to {telegram_id}: {e}")

