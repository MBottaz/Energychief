# bot/messages.py

# All user-facing strings live here.
# In Phase 9 (multi-tenant), each CER instance will have its own
# version of this file — same keys, different text/branding.

BOT_NAME = "Energychief"

START = (
    "👋 Hello {first_name}! I'm {bot_name}.\n\n"
    "I help you decide whether it's more convenient to heat with your "
    "heat pump or your gas boiler, based on real-time energy prices and weather.\n\n"
    "Type /help to see all available commands."
)

HELP = (
    "🤖 *{bot_name} — Available Commands*\n\n"
    "/start — Welcome message\n"
    "/help — Show this help\n"
    "/status — Current bot status\n"
    "/setup — Configure your energy profile\n\n"
    "_More commands will be added as the bot grows._"
)

STATUS = (
    "✅ *Bot Status*\n\n"
    "• Bot: {bot_name} — running\n"
    "• Database: not connected yet _(Phase 5)_\n"
    "• Weather API: not connected yet _(Phase 6)_\n"
    "• Enode API: not connected yet _(Phase 7)_\n"
    "• Energy model: not loaded yet _(Phase 8)_"
)

SETUP_ASK_HEATING = (
    "⚙️ Let's set up your energy profile.\n\n"
    "What heating system do you have?"
)

SETUP_ASK_ELECTRICITY_RATE = (
    "💡 What is your current electricity rate?\n"
    "Enter the price in *€/kWh* (e.g. `0.25`)"
)

SETUP_ASK_GAS_RATE = (
    "🔥 What is your current gas rate?\n"
    "Enter the price in *€/Sm³* (e.g. `0.95`)"
)

SETUP_CONFIRM = (
    "✅ *Setup saved!*\n\n"
    "• Heating system: {heating}\n"
    "• Electricity rate: {electricity_rate} €/kWh\n"
    "• Gas rate: {gas_rate} €/Sm³\n\n"
    "_You can run /setup again at any time to update these._"
)

SETUP_INVALID_ELECTRICITY_RATE = (
    "⚠️ That doesn't look right.\n"
    "Please enter a *positive number* for the electricity rate in €/kWh.\n"
    "Example: `0.25`"
)

SETUP_INVALID_GAS_RATE = (
    "⚠️ That doesn't look right.\n"
    "Please enter a *positive number* for the gas rate in €/Sm³.\n"
    "Example: `0.95`"
)
SETUP_CANCELLED = "❌ Setup cancelled. Run /setup whenever you're ready."
