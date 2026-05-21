# bot/handlers.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from bot import messages
from bot.validators import parse_positive_float
from bot.database import upsert_user_by_telegram, get_user_by_telegram_id

ASK_HEATING, ASK_ELECTRICITY_RATE, ASK_GAS_RATE = range(3)


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
            f"  – Heating: {row['heating']}\n"
            f"  – Electricity: {row['electricity_rate']} €/kWh\n"
            f"  – Gas: {row['gas_rate']} €/Sm³"
        )
    else:
        db_status = "• User profile: ❌ not set up yet — run /setup"

    text = messages.STATUS.format(bot_name=messages.BOT_NAME, db_status=db_status)
    await update.message.reply_text(text, parse_mode="Markdown")


async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Heat pump"], ["Gas boiler"], ["Both"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(messages.SETUP_ASK_HEATING, reply_markup=reply_markup)
    return ASK_HEATING


async def received_heating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["heating"] = update.message.text
    await update.message.reply_text(
        messages.SETUP_ASK_ELECTRICITY_RATE,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    return ASK_ELECTRICITY_RATE


async def received_electricity_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = parse_positive_float(update.message.text)
    if value is None:
        await update.message.reply_text(
            messages.SETUP_INVALID_ELECTRICITY_RATE, parse_mode="Markdown"
        )
        return ASK_ELECTRICITY_RATE
    context.user_data["electricity_rate"] = value
    await update.message.reply_text(messages.SETUP_ASK_GAS_RATE, parse_mode="Markdown")
    return ASK_GAS_RATE


async def received_gas_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = parse_positive_float(update.message.text)
    if value is None:
        await update.message.reply_text(
            messages.SETUP_INVALID_GAS_RATE, parse_mode="Markdown"
        )
        return ASK_GAS_RATE

    context.user_data["gas_rate"] = value
    user = update.effective_user

    # Persist to database
    upsert_user_by_telegram(
        telegram_id=user.id,
        first_name=user.first_name,
        heating=context.user_data["heating"],
        electricity_rate=context.user_data["electricity_rate"],
        gas_rate=context.user_data["gas_rate"],
    )

    summary = messages.SETUP_CONFIRM.format(
        heating=context.user_data["heating"],
        electricity_rate=context.user_data["electricity_rate"],
        gas_rate=context.user_data["gas_rate"],
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        messages.SETUP_CANCELLED, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
