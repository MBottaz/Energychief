from telegram import Update
from telegram.ext import ContextTypes

from frontend import messages
from shared.database import get_user_by_telegram_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        messages.START.format(first_name=user.first_name, bot_name=messages.BOT_NAME)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        messages.HELP.format(bot_name=messages.BOT_NAME), parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    row = get_user_by_telegram_id(user.id)

    if row:
        db_status = (
            f"• User profile: ✅ found\n"
            f"  – Heating: {row.heating}\n"
            f"  – Electricity: {row.electricity_rate} €/kWh\n"
            f"  – Gas: {row.gas_rate} €/Sm³"
        )
    else:
        db_status = "• User profile: ❌ not set up yet — run /setup"

    text = messages.STATUS.format(bot_name=messages.BOT_NAME, db_status=db_status)
    await update.message.reply_text(text, parse_mode="Markdown")
