"""
Telegram handlers for REC energy data — reads from local database.
"""

from telegram import Update
from telegram.ext import ContextTypes

from shared.database import (
    get_user_by_telegram_id,
    get_meters_for_user,
    get_latest_reading_for_meter,
)


async def handle_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row = get_user_by_telegram_id(update.effective_user.id)
    if row is None:
        await update.message.reply_text(
            "Non sei ancora registrato. Usa /start per cominciare."
        )
        return

    meters = get_meters_for_user(row.user_id)
    if not meters:
        await update.message.reply_text(
            "Nessun contatore collegato. Usa /collegacontatore per iniziare."
        )
        return

    lines = []
    for meter in meters:
        reading = get_latest_reading_for_meter(meter.meter_id)

        brand = meter.producer or "Sconosciuto"
        site = meter.site_name or ""

        if reading:
            signed_power = -reading.power_kw
            if signed_power > 0:
                cons, prod = "0 W", f"{signed_power:.0f} W"
            elif signed_power < 0:
                cons, prod = f"{abs(signed_power):.0f} W", "0 W"
            else:
                cons = prod = "0 W"
            updated = reading.timestamp
        else:
            cons = prod = "N/A"
            updated = "N/D"

        site_str = f" ({site})" if site else ""
        lines.append(
            f"*{brand}*{site_str}\n"
            f"  Consumo attuale: {cons}\n"
            f"  Produzione attuale: {prod}\n"
            f"  Ultimo aggiornamento: {updated}"
        )

    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")