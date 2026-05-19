from telegram import Update
from telegram.ext import ContextTypes
from src.energychief.bot import messages

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command.
    """
    await update.message.reply_text(messages.START_MESSAGE)
    await update.message.reply_text(messages.HELP_MESSAGE)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /help command.
    """
    await update.message.reply_text(messages.HELP_MESSAGE)
