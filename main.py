# main.py
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from bot.database import init_db, seed_recs_from_csv
from bot.bhandlers import (
    start,
    help_command,
    status,
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

from bot.handlers.enode_handler import handle_link_meter, handle_energy

from bot.services.rec_monitor import check_rec_and_notify


def build_setup_conversation() -> ConversationHandler:
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


def main() -> None:
    # Initialise DB (creates tables if they don't exist)
    init_db()
    
    # Seed RECs from CSV
    seeded_count = seed_recs_from_csv("recs_data.csv")
    if seeded_count > 0:
        print(f"Seeded {seeded_count} RECs from CSV.")
    elif seeded_count == 0:
        # It might be 0 because they are already there, 
        # or because the file is missing.
        # But since we are in main, let's just print a neutral message.
        print("Database ready (RECs already seeded or CSV empty).")
    else:
        print("Database ready.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(build_setup_conversation())
    app.add_handler(CommandHandler("collegacontatore", handle_link_meter))
    app.add_handler(CommandHandler("energia", handle_energy))

    # Register the periodic REC monitoring job
    if app.job_queue:
        app.job_queue.run_repeating(
            check_rec_and_notify,
            interval=3600,   # every 60 minutes
            first=10,        # start 10 seconds after bot launch
        )
        print("REC monitoring job scheduled.")
    else:
        print("Warning: JobQueue not available. REC monitoring will not run.")

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
