from telegram import Update
from telegram.ext import ContextTypes

from frontend import messages
from shared.database import get_user_by_telegram_id, get_meters_for_user


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        messages.HELP.format(bot_name=messages.BOT_NAME), parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    row = get_user_by_telegram_id(user.id)

    if row:
        meters = get_meters_for_user(row.user_id)
        if meters:
            meter_info = f"• Contatori collegati: {len(meters)}"
        else:
            meter_info = "• Contatori collegati: nessuno — usa /collegacontatore"

        db_status = (
            f"• User profile: ✅ found\n"
            f"{meter_info}"
        )
    else:
        db_status = "• User profile: ❌ not set up yet — run /setup"

    text = messages.STATUS.format(bot_name=messages.BOT_NAME, db_status=db_status)
    await update.message.reply_text(text, parse_mode="Markdown")
