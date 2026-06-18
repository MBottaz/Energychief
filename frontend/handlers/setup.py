from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from frontend import messages
from shared.database import (
    upsert_user_by_telegram,
    get_all_recs,
    upsert_meter,
)

ASK_POD, ASK_REC = range(2)


async def setup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(messages.SETUP_ASK_POD, parse_mode="Markdown")
    return ASK_POD


async def received_pod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pod = update.message.text.strip()
    if not pod:
        await update.message.reply_text("⚠️ Inserisci un POD valido.")
        return ASK_POD

    context.user_data["pod"] = pod

    # Show REC selection list
    recs = get_all_recs()
    if not recs:
        await update.message.reply_text("⚠️ Nessuna REC trovata nel sistema. Contatta un amministratore.")
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

    user = update.effective_user

    # Create/update the user in the database
    db_user = upsert_user_by_telegram(
        telegram_id=user.id,
        first_name=user.first_name,
        rec_id=selected_rec_id,
    )

    # Store the POD as a meter linked to this user
    pod = context.user_data.get("pod", "")
    if pod:
        upsert_meter(meter_id=pod, owner_user_id=db_user.user_id)

    summary = messages.SETUP_CONFIRM.format(
        pod=pod,
        rec_name=selected_rec_name,
    )
    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END


async def setup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        messages.SETUP_CANCELLED, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END