from telegram import Update
from telegram.ext import ContextTypes
from shared.database import get_user_by_telegram_id
from backend.enode_api import create_link_session, get_user_meters, get_meter


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


async def handle_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    enode_user_id = _resolve_enode_user_id(update.effective_user.id)
    if enode_user_id is None:
        await update.message.reply_text(
            "Non sei ancora registrato. Usa /start per cominciare."
        )
        return

    try:
        meters = await get_user_meters(enode_user_id)
        if not meters:
            await update.message.reply_text(
                "Nessun contatore collegato. Usa /collegacontatore per iniziare."
            )
            return

        lines = []
        for m in meters:
            meter_id = m["id"]
            brand = m.get("information", {}).get("brand", "Sconosciuto")
            site = m.get("information", {}).get("siteName", "")
            reachable = m.get("isReachable", False)

            detail = await get_meter(meter_id)
            energy = detail.get("energyState", {})

            # Enode API: power = net flow (positive = consumed, negative = produced).
            # We store and display it signed: positive = production, negative = consumption.
            signed_power: float | None = energy.get("power")
            last_updated = energy.get("lastUpdated", "N/A")

            if signed_power is not None:
                signed_power = -signed_power  # invert sign
                if signed_power > 0:
                    prod_str = f"{signed_power:.0f} W"
                    cons_str = "0 W"
                elif signed_power < 0:
                    cons_str = f"{abs(signed_power):.0f} W"
                    prod_str = "0 W"
                else:
                    cons_str = "0 W"
                    prod_str = "0 W"
            else:
                cons_str = "N/A"
                prod_str = "N/A"

            status = "🟢" if reachable else "🔴"

            lines.append(
                f"{status} *{brand}* ({site})\n"
                f"  Consumo attuale: {cons_str}\n"
                f"  Produzione attuale: {prod_str}\n"
                f"  Aggiornato: {last_updated}"
            )

        await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Errore nel recupero dati: {e}")
