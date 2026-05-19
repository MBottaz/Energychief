from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)
import re
from src.energychief.bot import messages
from src.energychief.db import repository
from src.energychief.utils import pod
from src.energychief.config import settings

# Conversation States
ROLE, POD, ENODE_LINK, DEVICE_CONFIRM, COORDINATES, CAPACITY, THRESHOLD, NOTIFICATION_PREFS, CONFIRM = range(9)

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Starts the onboarding process.
    """
    keyboard = [
        [InlineKeyboardButton("Prosumer ⚡", callback_data="role_prosumer")],
        [InlineKeyboardButton("Consumer 🏠", callback_data="role_consumer")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(messages.ROLE_QUESTION, reply_markup=reply_markup)
    return ROLE

async def handle_role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles role selection from inline buttons.
    """
    query = update.callback_query
    await query.answer()
    role = query.data.split("_")[1]
    context.user_data["role"] = role

    if role == "consumer":
        return await start_pod_collection(update, context)
    else:
        return await start_pod_collection(update, context)

async def start_pod_collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Moves to POD collection.
    """
    # If it's a callback query, use it to reply
    if hasattr(update, "callback_query"):
        await update.callback_query.message.reply_text(messages.POD_QUESTION)
    else:
        await update.message.reply_text(messages.POD_QUESTION)
    return POD

async def handle_pod_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles POD input and validation.
    """
    pod_str = update.message.text.strip()
    if not pod.validate_pod(pod_str):
        await update.message.reply_text(messages.POD_ERROR)
        return POD

    context.user_data["pod"] = pod_str
    context.user_data["pod_prefix"] = pod.extract_pod_prefix(pod_str)
    
    cer = await repository.get_cer_by_prefix(context.user_data["pod_prefix"])
    
    if not cer:
        if context.user_data["role"] == "prosumer":
            # Create CER automatically for prosumer
            # We'll use a default name for now
            cer_id = await repository.create_cer(f"CER {context.user_data['pod_prefix']}", context.user_data["pod_prefix"])
            context.user_data["cer_id"] = cer_id
        else:
            await update.message.reply_text(messages.CER_NOT_FOUND)
            return ConversationHandler.END
    else:
        context.user_data["cer_id"] = cer["id"]

    if context.user_data["role"] == "prosumer":
        return await start_enode_link(update, context)
    else:
        return await start_notification_prefs(update, context)

async def start_enode_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generates Enode Link for prosumer.
    """
    from src.energychief.adapters.enode import EnodeAdapter # Local import to avoid circularity if any
    
    # We don't have the Enode client ID here directly in the context easily, 
    # but we have the settings.
    # Note: In production, the client_id for Link is different or specific. 
    # Here we use the general one from settings.
    
    user_id = context.user.id
    # Link URL construction
    # https://link.{env}.enode.io?client_id={id}&user_id={telegram_id}&scopes=meter:read:data
    env = settings.ENODE_ENVIRONMENT
    url = f"https://link.{env}.enode.io?client_id={settings.ENODE_CLIENT_ID}&user_id={user_id}&scopes=meter:read:data"
    
    context.user_data["enode_link_url"] = url
    
    keyboard = [[InlineKeyboardButton(messages.ENODE_LINK_BUTTON, callback_data="enode_linked")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(messages.ENODE_LINK_MESSAGE.format(url=url), reply_markup=reply_markup)
    return ENODE_LINK

async def handle_enode_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles clicking "I have completed the link".
    """
    query = update.callback_query
    await query.answer()
    
    # Discovery
    from src.energychief.adapters.enode import EnodeAdapter
    adapter = EnodeAdapter(enode_user_id=str(context.user.id))
    try:
        devices = await adapter.discover_devices()
        if not devices.get("meters"):
            await query.message.reply_text(messages.ENODE_NO_DEVICES)
            return ConversationHandler.END
        
        # If exactly one meter, auto-select
        if len(devices["meters"]) == 1:
            meter_id = devices["meters"][0]["id"]
            context.user_data["enode_meter_id"] = meter_id
            # Move to next step
            return await start_coordinates_input(update, context)
        else:
            # For now, we simplify: just pick the first one or ask. 
            # To keep it simple for MVP, we pick the first one and ask for confirmation if multiple.
            # But let's actually ask.
            context.user_data["available_meters"] = devices["meters"]
            await query.message.reply_text("I found multiple meters. Please select one:")
            keyboard = []
            for m in devices["meters"]:
                keyboard.append([InlineKeyboardButton(f"{m['name']} ({m['id']})", callback_data=f"select_meter_{m['id']}")])
            await query.message.reply_text("Select a meter:", reply_markup=InlineKeyboardMarkup(keyboard))
            return DEVICE_CONFIRM
            
    except Exception as e:
        await query.message.reply_text(f"Error during discovery: {e}")
        return ConversationHandler.END
    finally:
        await adapter.close()

async def handle_meter_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles meter selection from list.
    """
    query = update.callback_query
    await query.answer()
    meter_id = query.data.replace("select_meter_", "")
    context.user_data["enode_meter_id"] = meter_id
    return await start_coordinates_input(update, context)

async def start_coordinates_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Moves to coordinates input.
    """
    # If it's a callback, we might need to use query.message
    msg = update.callback_query.message if hasattr(update, "callback_query") else update.message
    await msg.reply_text(messages.COORDINATES_QUESTION)
    return COORDINATES

async def handle_coordinates_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles lat/lon input.
    """
    text = update.message.text
    try:
        # Expecting "lat, lon"
        parts = text.split(",")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        context.user_data["latitude"] = lat
        context.user_data["longitude"] = lon
    except ValueError:
        await update.message.reply_text("Please use the format: 'lat, lon' (e.g., 45.123, 9.456)")
        return COORDINATES

    return await start_capacity_input(update, context)

async def start_capacity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Moves to capacity input.
    """
    await update.message.reply_text(messages.CAPACITY_QUESTION)
    return CAPACITY

async def handle_capacity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles capacity input.
    """
    try:
        val = float(update.message.text.strip())
        context.user_data["capacity_kwp"] = val
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return CAPACITY

    return await start_threshold_input(update, context)

async def start_threshold_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Moves to threshold input.
    """
    await update.message.reply_text(messages.THRESHOLD_QUESTION)
    return THRESHOLD

async def handle_threshold_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles threshold input.
    """
    try:
        val = float(update.message.text.strip())
        context.user_data["export_threshold_kw"] = val
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return THRESHOLD

    return await start_notification_prefs(update, context)

async def start_notification_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Moves to notification preferences.
    """
    await update.message.reply_text(messages.NOTIFICATION_PREFS_QUESTION)
    return NOTIFICATION_PREFS

async def handle_notification_prefs_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles notification prefs.
    """
    choice = update.message.text.strip().lower()
    if choice in ["sì", "si", "yes", "y"]:
        context.user_data["notifications_enabled"] = 1
    elif choice in ["no"]:
        context.user_data["notifications_enabled"] = 0
    else:
        await update.message.reply_text("Please answer with 'Sì' or 'No'.")
        return NOTIFICATION_PREFS

    return await start_confirmation(update, context)

async def start_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Summarizes and asks for confirmation.
    """
    data = context.user_data
    summary = (
        f"Role: {data.get('role')}\n"
        f"POD: {data.get('pod')}\n"
        f"Enode Meter: {data.get('enode_meter_id')}\n"
        f"Lat/Lon: {data.get('latitude')}, {data.get('longitude')}\n"
        f"Capacity: {data.get('capacity_kwp')} kWp\n"
        f"Threshold: {data.get('export_threshold_kw')} kW\n"
        f"Notifications: {'Enabled' if data.get('notifications_enabled') else 'Disabled'}"
    )
    
    keyboard = [
        [InlineKeyboardButton("Conferma ✅", callback_data="confirm_yes")],
        [InlineKeyboardButton("Modifica ✏️", callback_data="confirm_no")],
        [InlineKeyboardButton("Annulla ❌", callback_data="confirm_cancel")]
    ]
    await update.message.reply_text(messages.CONFIRM_SUMMARY.format(summary=summary), reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

async def handle_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Finalizes registration.
    """
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "confirm_yes":
        data = context.user_data
        # SAVE TO DB
        try:
            # 1. Member
            member_id = await repository.create_member(
                telegram_id=context.user.id,
                telegram_username=context.user.username,
                cer_id=data['cer_id'],
                role=data['role'],
                pod=data['pod']
            )
            
            # 2. Plant (if prosumer)
            if data['role'] == 'prosumer':
                await repository.create_prosumer_plant(
                    member_id=member_id,
                    enode_user_id=str(context.user.id),
                    latitude=data['latitude'],
                    longitude=data['longitude'],
                    enode_meter_id=data.get('enode_meter_id'),
                    capacity_kwp=data.get('capacity_kwp'),
                    export_threshold_kw=data.get('export_threshold_kw', 1.0)
                )
            
            # 3. Notification Prefs
            await repository.create_notification_preference(
                member_id=member_id,
                enabled=data.get('notifications_enabled', 1)
            )
            
            await query.message.reply_text(messages.CONFIRM_SUCCESS)
        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            await query.message.reply_text(messages.ERROR_GENERIC)
        return ConversationHandler.END

    elif choice == "confirm_no":
        await query.message.reply_text("To modify settings, please restart /registra.")
        return ConversationHandler.END
    
    else: # cancel
        await query.message.reply_text(messages.CONFIRM_CANCELLED)
        return ConversationHandler.END

def get_onboarding_handler() -> ConversationHandler:
    """
    Returns the ConversationHandler for onboarding.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("registra", start_onboarding)],
        states={
            ROLE: [CallbackQueryHandler(handle_role_selection, pattern="^role_")],
            POD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pod_input)],
            ENODE_LINK: [CallbackQueryHandler(handle_enode_link_callback, pattern="^enode_linked$")],
            DEVICE_CONFIRM: [CallbackQueryHandler(handle_meter_selection, pattern="^select_meter_")],
            COORDINATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coordinates_input)],
            CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_capacity_input)],
            THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold_input)],
            NOTIFICATION_PREFS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notification_prefs_input)],
            CONFIRM: [CallbackQueryHandler(handle_confirmation_callback, pattern="^confirm_")],
        },
        fallbacks=[CommandHandler("registra", start_onboarding)],
    )
