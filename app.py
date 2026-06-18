"""
app.py — FastAPI entry point.

Merges the old main_backend.py and main_frontend.py into a single
process. Uses a lifespan context manager to:
  - Initialise the database
  - Start the Enode polling loop as a background asyncio task
  - Build the PTB Application, initialise it, start polling (non-blocking)
  - On shutdown: cancel the background task, stop the PTB app
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from telegram import Update

from shared.config import WEBHOOK_BASE_URL, ENODE_WEBHOOK_SECRET
from shared.engine import engine
from shared.models import Base
from shared.database import seed_recs_from_csv
from backend.rec_monitor import collect_and_store_readings
from backend.enode_webhook_handler import verify_enode_signature, process_enode_event
from frontend.telegram_app import build_telegram_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    seeded = seed_recs_from_csv("recs_data.csv")
    if seeded > 0:
        print(f"Seeded {seeded} RECs from CSV.")
    else:
        print("Database ready.")

    # Polling interval: 1 hour normally, 24 hours if webhooks are configured (safety net)
    poll_interval = 3600 * 24 if ENODE_WEBHOOK_SECRET else 3600
    backend_task = asyncio.create_task(_backend_polling_loop(interval=poll_interval))

    tg_app = build_telegram_app()
    await tg_app.initialize()

    if WEBHOOK_BASE_URL:
        # ── Webhook mode ──
        webhook_url = f"{WEBHOOK_BASE_URL}/webhooks/telegram"
        await tg_app.bot.set_webhook(url=webhook_url)
        await tg_app.job_queue.start()
        app.state.tg_app = tg_app
        print(f"Telegram webhook set to {webhook_url}")
    else:
        # ── Polling mode (fallback) ──
        await tg_app.updater.start_polling()  # starts fetching updates from Telegram
        await tg_app.start()                  # starts update processor + job queue
        app.state.tg_app = tg_app
        print("Telegram polling started.")

    print("FastAPI + Telegram + backend loop — running.")

    yield  # ── app runs here ──

    # ── SHUTDOWN ──
    backend_task.cancel()
    try:
        await backend_task
    except asyncio.CancelledError:
        pass

    if WEBHOOK_BASE_URL:
        await tg_app.bot.delete_webhook()
        await tg_app.job_queue.stop()
    else:
        await tg_app.updater.stop()  # stop polling first
        await tg_app.stop()
    await tg_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhooks/telegram")
async def telegram_webhook(request: Request):
    """Receives Telegram updates via webhook and feeds them to PTB."""
    data = await request.json()
    update = Update.de_json(data, request.app.state.tg_app.bot)
    await request.app.state.tg_app.process_update(update)
    return Response(status_code=200)


@app.post("/webhooks/enode")
async def enode_webhook(request: Request):
    """
    Receive real-time events from Enode.

    Enode sends an array of event objects as the request body.
    We verify the HMAC-SHA1 signature, respond 200 immediately,
    and process events in the background.
    """
    raw_body = await request.body()

    # Verify signature
    signature = request.headers.get("x-enode-signature", "")
    delivery_id = request.headers.get("x-enode-delivery")

    if not verify_enode_signature(raw_body, signature):
        print(f"WARNING: Invalid Enode webhook signature (delivery={delivery_id})")
        return Response(status_code=403, content="Invalid signature")

    # Parse events
    try:
        events = json.loads(raw_body)
    except json.JSONDecodeError:
        print(f"WARNING: Invalid JSON payload from Enode (delivery={delivery_id})")
        return Response(status_code=400, content="Invalid JSON")

    if not isinstance(events, list):
        events = [events]

    print(f"Webhook: received {len(events)} event(s) from Enode (delivery={delivery_id})")

    # Process events in background (respond 200 first — Enode has a 5s timeout)
    async def _process():
        for event in events:
            try:
                await process_enode_event(event, delivery_id)
            except Exception as e:
                print(f"Webhook: error processing event {event.get('event')}: {e}")

    asyncio.create_task(_process())

    return Response(status_code=200)


async def _backend_polling_loop(interval: int = 3600):
    """Background task that polls Enode at a regular interval.

    When webhooks are active (ENODE_WEBHOOK_SECRET is set), the interval
    is extended to 24h as a safety-net/backfill. Otherwise it runs every 60 min.
    """
    while True:
        try:
            await collect_and_store_readings()
        except Exception as e:
            print(f"Backend polling error: {e}")
        await asyncio.sleep(interval)