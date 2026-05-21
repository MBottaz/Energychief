# main.py
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from bot.database import init_db
from bot.handlers import (
    start,
    help_command,
    status,
    setup_start,
    received_heating,
    received_electricity_rate,
    received_gas_rate,
    setup_cancel,
    ASK_HEATING,
    ASK_ELECTRICITY_RATE,
    ASK_GAS_RATE,
)


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
        },
        fallbacks=[CommandHandler("cancel", setup_cancel)],
    )


def main() -> None:
    # Initialise DB (creates tables if they don't exist)
    init_db()
    print("Database ready.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(build_setup_conversation())

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
