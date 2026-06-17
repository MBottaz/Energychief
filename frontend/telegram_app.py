"""
frontend/telegram_app.py — PTB Application factory.

Builds and returns a configured telegram.ext.Application for use
inside the FastAPI lifespan.
"""

import datetime
from zoneinfo import ZoneInfo

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from shared.config import TELEGRAM_TOKEN
from shared.database import (
    get_all_recs,
    get_latest_power_per_meter,
    get_users_in_rec,
    update_last_notified,
)
from frontend.handlers.general import start, help_command, status
from frontend.handlers.setup import (
    setup_start,
    received_heating,
    received_electricity_rate,
    received_gas_rate,
    received_rec,
    setup_cancel,
    ASK_HEATING,
    ASK_ELECTRICITY_RATE,
    ASK_GAS_RATE,
    ASK_REC,
)
from frontend.handlers.enode import handle_link_meter
from frontend.handlers.rec import handle_energy


async def check_recs_and_notify(context) -> None:
    """
    JobQueue task: read REC energy data from the DB (no Enode call)
    and send notifications immediately if conditions are met.
    """
    try:
        rome_tz = ZoneInfo("Europe/Rome")
        now_rome = datetime.datetime.now(rome_tz)

        # Time window guard (07:00–22:00)
        if not (7 <= now_rome.hour < 22):
            return

        recs = get_all_recs()
        for rec in recs:
            rec_id = rec.rec_id

            latest = get_latest_power_per_meter(rec_id)
            if not latest:
                continue

            sum_kw = sum(row["power_kw"] for row in latest)

            users = get_users_in_rec(rec_id)
            for user in users:
                telegram_id = user.telegram_id
                threshold = user.threshold_kwh
                interval_h = user.notification_interval_hours
                last_str = user.last_notified_at

                if sum_kw < threshold:
                    continue

                should_notify = False
                if last_str is None:
                    should_notify = True
                else:
                    try:
                        last_at = datetime.datetime.fromisoformat(last_str)
                        if last_at.tzinfo is None:
                            last_at = last_at.replace(tzinfo=datetime.timezone.utc)
                        diff = now_rome.astimezone(datetime.timezone.utc) - last_at
                        if diff.total_seconds() >= (interval_h * 3600):
                            should_notify = True
                    except ValueError:
                        should_notify = True

                if should_notify:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text="⚡ Nella tua CER è disponibile energia, è un buon momento per accendere un elettrodomestico!"
                    )
                    update_last_notified(telegram_id)
                    print(f"Notification sent to user {telegram_id}")
    except Exception as e:
        print(f"REC check error: {e}")


def _build_setup_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("setup", setup_start)],
        states={
            ASK_HEATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_heating)
            ],
            ASK_ELECTRICITY_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_electricity_rate)
            ],
            ASK_GAS_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_gas_rate)
            ],
            ASK_REC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_rec)
            ],
        },
        fallbacks=[CommandHandler("cancel", setup_cancel)],
    )


def build_telegram_app():
    """Build and return a configured PTB Application (polling mode)."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(_build_setup_conversation())
    app.add_handler(CommandHandler("collegacontatore", handle_link_meter))
    app.add_handler(CommandHandler("energia", handle_energy))

    if app.job_queue:
        app.job_queue.run_repeating(
            check_recs_and_notify, interval=3600, first=60
        )
        print("REC notification check scheduled (every 60 min).")
    else:
        print("Warning: JobQueue not available. Notifications will not be sent automatically.")

    return app