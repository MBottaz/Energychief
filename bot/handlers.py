# bot/handlers.py
from telegram import Update
from telegram.ext import ContextTypes

from bot import messages


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to /start."""
    user = update.effective_user
    text = messages.START.format(
        first_name=user.first_name,
        bot_name=messages.BOT_NAME,
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to /help."""
    text = messages.HELP.format(bot_name=messages.BOT_NAME)
    await update.message.reply_text(text, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responds to /status."""
    text = messages.STATUS.format(bot_name=messages.BOT_NAME)
    await update.message.reply_text(text, parse_mode="Markdown")
