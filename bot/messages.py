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
    "/status — Current bot status\n\n"
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
