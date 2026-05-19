"""
Bot messages in Italian.
Used by various handlers to maintain consistent tone and language.
"""

# General
START_MESSAGE = "Ciao! 👋 Benvenuto su EnergyChief. Il tuo assistente per la Comunità Energetica! ⚡"
HELP_MESSAGE = (
    "Ecco cosa posso fare per te:\n\n"
    "🔹 /registra - Per entrare a far parte della CER (Prosumer o Consumer)\n"
    "🔹 /stato - Per vedere l'ultimo stato energetico della tua CER\n"
    "🔹 /impostazioni - Per modificare le tue preferenze di notifica\n"
    "🔹 /aiuto - Per vedere questo messaggio"
)

# Onboarding
ROLE_QUESTION = "Sei un prosumer (hai un impianto FV) o un consumer?"
POD_QUESTION = "Inserisci il tuo codice POD (formato IT001E12345678):"
POD_ERROR = "Codice POD non valido. Assicurati che sia nel formato corretto (es. IT001E12345678)."
CER_NOT_FOUND = "Nessuna CER trovata per la tua cabina primaria. Contatta l'amministratore."
ENODE_LINK_MESSAGE = (
    "Per collegare il tuo contatore, clicca sul link qui sotto e segui le istruzioni di Enode:\n\n"
    "{url}\n\n"
    "Dopo aver completato la procedura, premi il tasto qui sotto! 👇"
)
ENODE_LINK_BUTTON = "✅ Ho completato il collegamento"
ENODE_NO_DEVICES = "Nessun contatore trovato dopo il collegamento. Riprova."
COORDINATES_QUESTION = "Inserisci le coordinate del tuo impianto (latitudine, longitudine). "
                      "Puoi lasciarle vuote se Enode ha già rilevato la posizione."
CAPACITY_QUESTION = "Qual è la potenza nominale del tuo impianto in kWp? (es. 3.5)"
THRESHOLD_QUESTION = "Soglia di esportazione in kW per le notifiche (default: 1.0):"
NOTIFICATION_PREFS_QUESTION = "Configurazione notifiche:\n"
                               "Vuoi ricevere le notifiche attive? (Sì/No)"
CONFIRM_SUMMARY = "Riepilogo dati:\n\n{summary}\n\nConfermi i dati?"
CONFIRM_SUCCESS = "✅ Registrazione completata con successo!"
CONFIRM_CANCELLED = "❌ Registrazione annullata."

# Status
STATUS_NO_DATA = "Nessun dato recente disponibile per la tua CER."
STATUS_DATA_TEMPLATE = (
    "📊 *Stato attuale della CER*\n"
    "---------------------------\n"
    "⚡ Potenza in rete: {grid_power:.2f} kW\n"
    "📅 Ultima lettura: {timestamp}\n"
    "🏠 Stato: {status_text}"
)

# Settings
SETTINGS_MENU = "⚙️ *Impostazioni Notifiche*\nCosa desideri modificare?"
SETTINGS_THRESHOLD = "Modifica la soglia di esportazione (kW):"
SETTINGS_MIN_POWER = "Modifica la potenza minima di interesse (kW):"
SETTINGS_QUIET_HOURS = "Modifica le ore di silenzio (es. 22:00 - 06:00):"
SETTINGS_SAVE_SUCCESS = "✅ Impostazioni aggiornate!"

# Errors
ERROR_GENERIC = "⚠️ Si è verificato un errore. Riprova più tardi."
ERROR_DB = "⚠️ Errore durante l'accesso al database."
