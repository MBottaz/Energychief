from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from frontend import messages
from frontend.validators import parse_positive_float
from shared.database import upsert_user_by_telegram, get_all_recs

ASK_HEATING, ASK_ELECTRICITY_RATE, ASK_GAS_RATE, ASK_REC = range(4)


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

    # Fetch RECs to show them to the user
    recs = get_all_recs()
    if not recs:
        await update.message.reply_text("⚠️ No RECs found in the system. Please contact an administrator.")
        return ConversationHandler.END

    rec_options = []
    for i, rec in enumerate(recs, 1):
        rec_options.append(f"{i}. {rec.name}")

    rec_list_text = "\n".join(rec_options)
    await update.message.reply_text(
        f"{messages.SETUP_ASK_REC}\n\n{rec_list_text}",
        parse_mode="Markdown"
    )
    return ASK_REC


async def received_rec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.strip()
    recs = get_all_recs()

    selected_rec_id = None
    selected_rec_name = ""

    # Try to match by number
    if user_input.isdigit():
        idx = int(user_input) - 1
        if 0 <= idx < len(recs):
            selected_rec_id = recs[idx].rec_id
            selected_rec_name = recs[idx].name

    # If not matched by number, try to match by name
    if selected_rec_id is None:
        for rec in recs:
            if rec.name.lower() == user_input.lower():
                selected_rec_id = rec.rec_id
                selected_rec_name = rec.name
                break

    if selected_rec_id is None:
        await update.message.reply_text(messages.SETUP_REC_NOT_FOUND, parse_mode="Markdown")
        return ASK_REC

    context.user_data["rec_id"] = selected_rec_id
    context.user_data["rec_name"] = selected_rec_name
    user = update.effective_user

    # Persist to database
    upsert_user_by_telegram(
        telegram_id=user.id,
        first_name=user.first_name,
        heating=context.user_data["heating"],
        electricity_rate=context.user_data["electricity_rate"],
        gas_rate=context.user_data["gas_rate"],
        rec_id=selected_rec_id,
    )

    summary = messages.SETUP_CONFIRM.format(
        heating=context.user_data["heating"],
        electricity_rate=context.user_data["electricity_rate"],
        gas_rate=context.user_data["gas_rate"],
        rec_name=selected_rec_name
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        messages.SETUP_CANCELLED, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
