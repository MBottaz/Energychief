# bot/handlers.py
from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}! I'm Energychief.\n"
        "I'll help you decide when to use your heat pump vs. gas boiler.\n\n"
        "Type /help to see what I can do."
    )
