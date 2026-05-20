# main.py
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN
from bot.handlers import start, help_command, status


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register all command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))

    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
