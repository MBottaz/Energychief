# frontend/messages.py — User-facing strings.
# All UI text lives here for easy customisation.

BOT_NAME = "Energychief"

START = (
    "👋 Hello {first_name}! I'm {bot_name}.\n\n"
    "I help you decide whether it's more convenient to heat with your "
    "heat pump or your gas boiler, based on real-time energy prices and weather.\n\n"
    "Type /help to see all available commands."
)

HELP = (
    "🤖 *{bot_name} — Comandi Disponibili*\n\n"
    "/start — Messaggio di benvenuto\n"
    "/help — Mostra questo aiuto\n"
    "/status — Stato del bot e del tuo profilo\n"
    "/setup — Configura il tuo profilo energetico\n"
    "/collegacontatore — Collega il tuo contatore Enode\n"
    "/energia — Mostra i dati energetici dei tuoi contatori"
)

STATUS = (
    "✅ *Bot Status*\n\n"
    "{db_status}"
)
SETUP_ASK_POD = (
    "⚙️ Configuriamo il tuo profilo energetico.\n\n"
    "Inserisci il tuo **POD** (il codice del punto di prelievo, es. `AC001E00696`):"
)

SETUP_CONFIRM = (
    "✅ *Setup salvato!*\n\n"
    "• POD: {pod}\n"
    "• REC: {rec_name}\n\n"
    "_Puoi eseguire /setup di nuovo per aggiornare questi dati._"
)

SETUP_ASK_REC = (
    "🏘️ In quale REC sei membro?\n"
    "Inserisci il **numero** o il **nome** della comunità dalla lista:"
)

SETUP_REC_NOT_FOUND = (
    "⚠️ REC non trovato. Inserisci un nome o numero valido dalla lista."
)

SETUP_CANCELLED = "❌ Setup annullato. Usa /setup quando sei pronto."

