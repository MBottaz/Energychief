# frontend/messages.py — User-facing strings.
# All UI text lives here for easy customisation.

BOT_NAME = "Energychief"

START = (
    "👋 Ciao {first_name}! Sono {bot_name}.\n\n"
    "ti aiutero a capire come quando nella tua comunita energetica c'e energia disponibile. "
    "Puoi risparmiare fino a meta del costo dell'energia!\n\n"
    "Digira /help to see all available commands."
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
    "Inserisci il tuo **POD** (il codice del punto di prelievo, es. `IT001E1234567`):"
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

