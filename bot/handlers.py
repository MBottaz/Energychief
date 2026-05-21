# bot/handlers.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from bot import messages

# ---------------------------------------------------------------------------
# Conversation states — each integer represents a step in a multi-turn dialog.
# Named constants make the code readable. More states will be added in
# Phase 4 (validation loops) and Phase 8 (energy query flow).
# ---------------------------------------------------------------------------
ASK_HEATING, ASK_ELECTRICITY_RATE, ASK_GAS_RATE = range(3)


# ---------------------------------------------------------------------------
# Static command handlers (Phase 2)
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = messages.START.format(
        first_name=user.first_name,
        bot_name=messages.BOT_NAME,
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = messages.HELP.format(bot_name=messages.BOT_NAME)
    await update.message.reply_text(text, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = messages.STATUS.format(bot_name=messages.BOT_NAME)
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /setup conversation — collects heating system and energy tariffs
# ---------------------------------------------------------------------------

async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /setup command. Returns the next state."""
    keyboard = [["Heat pump"], ["Gas boiler"], ["Both"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(messages.SETUP_ASK_HEATING, reply_markup=reply_markup)
    return ASK_HEATING


async def received_heating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores heating choice, asks for electricity rate."""
    context.user_data["heating"] = update.message.text
    await update.message.reply_text(
        messages.SETUP_ASK_ELECTRICITY_RATE,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_ELECTRICITY_RATE

async def received_electricity_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validates and stores electricity rate, or loops back on bad input."""
    from bot.validators import parse_positive_float

    value = parse_positive_float(update.message.text)
    if value is None:
        await update.message.reply_text(
            messages.SETUP_INVALID_ELECTRICITY_RATE,
            parse_mode="Markdown",
        )
        return ASK_ELECTRICITY_RATE  # same state → bot asks again

    context.user_data["electricity_rate"] = value
    await update.message.reply_text(messages.SETUP_ASK_GAS_RATE, parse_mode="Markdown")
    return ASK_GAS_RATE


async def received_gas_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validates and stores gas rate, or loops back on bad input."""
    from bot.validators import parse_positive_float

    value = parse_positive_float(update.message.text)
    if value is None:
        await update.message.reply_text(
            messages.SETUP_INVALID_GAS_RATE,
            parse_mode="Markdown",
        )
        return ASK_GAS_RATE  # same state → bot asks again

    context.user_data["gas_rate"] = value

    summary = messages.SETUP_CONFIRM.format(
        heating=context.user_data["heating"],
        electricity_rate=context.user_data["electricity_rate"],
        gas_rate=context.user_data["gas_rate"],
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles /cancel during the conversation."""
    await update.message.reply_text(messages.SETUP_CANCELLED, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
