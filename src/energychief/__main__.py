from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from src.energychief.bot import messages
from src.energychief.bot.handlers.start import start_handler, help_handler
from src.energychief.bot.handlers.onboarding import get_onboarding_handler
from src.energychief.db.connection import init_db
from src.energychief.config import settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.energychief.services.polling import PollingService
from src.energychief.services.notifier import NotifierService
from src.energychief.services.forecast import ForecastService
from src.energychief.services.weather import WeatherService
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """
    Main entry point for the EnergyChief Telegram Bot.
    """
    # 1. Initialize Database
    await init_db()
    
    # 2. Initialize Telegram Application
    from telegram.ext import ApplicationBuilder
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # 3. Register Handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(get_onboarding_handler())
    
    # 4. Initialize Services
    notifier = NotifierService(application)
    polling_service = PollingService(notifier)
    weather_service = WeatherService()
    forecast_service = ForecastService(weather_service)
    
    # 5. Setup Scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Rome")
    
    # Polling job (every 60 min, 06-22)
    scheduler.add_job(
        polling_service.poll_all_prosumers,
        'cron',
        hour='6-22',
        minute='0',
        id='polling_job'
    )
    
    # Forecast job (07:00 daily)
    # Note: Implementation of send_forecast_job would need to iterate over CERs
    # For MVP we define the placeholder
    async def send_forecast_job():
        logger.info("Running daily forecast job...")
        # Implementation logic from prompt would go here
        pass

    scheduler.add_job(
        send_forecast_job,
        'cron',
        hour='7',
        minute='0',
        id='forecast_job'
    )
    
    scheduler.start()
    logger.info("Scheduler started.")

    # 6. Run the Bot
    logger.info("Starting Telegram bot polling...")
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the loop running until interrupted
        try:
            import asyncio
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            scheduler.shutdown()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
