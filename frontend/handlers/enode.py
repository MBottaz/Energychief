from telegram import Update
from telegram.ext import ContextTypes
from shared.database import get_user_by_telegram_id
from backend.enode_api import create_link_session


def _resolve_enode_user_id(telegram_id: int) -> str | None:
    """Returns the DB primary key as a string, or None if user not found."""
    row = get_user_by_telegram_id(telegram_id)
    if row is None:
        return None
    return str(row.user_id)


async def handle_link_meter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enode_user_id = _resolve_enode_user_id(update.effective_user.id)
    if enode_user_id is None:
        await update.message.reply_text(
            "Non sei ancora registrato. Usa /start per cominciare."
        )
        return

    try:
        link_url = await create_link_session(enode_user_id)
        await update.message.reply_text(
            f"Clicca qui per collegare il tuo contatore:\n{link_url}\n\n"
            "Una volta completato, torna qui e usa /energia per vedere i dati."
        )
    except Exception as e:
        await update.message.reply_text(f"Errore durante la creazione del link: {e}")


