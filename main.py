# main.py
from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN
from bot.handlers import start


def main() -> None:
    # Build the bot application using the token from config
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))

    # Start polling (checks Telegram for new messages every few seconds)
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
