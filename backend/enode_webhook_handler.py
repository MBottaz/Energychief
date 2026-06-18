"""
Enode webhook signature verification and event processing.

Extracted from app.py to keep the entry point focused on wiring.
"""

import hashlib
import hmac
import json

from shared.config import ENODE_WEBHOOK_SECRET
from shared.database import save_meter_reading


def verify_enode_signature(payload: bytes, signature_header: str) -> bool:
    """
    Verify that a webhook request originated from Enode.

    Enode signs the raw request body with HMAC-SHA1 using the secret
    provided when creating the webhook. The signature is sent in the
    ``x-enode-signature`` header in the format ``sha1=<hex_digest>``.
    """
    if not ENODE_WEBHOOK_SECRET:
        # No secret configured — skip verification (should only happen in dev)
        print("WARNING: ENODE_WEBHOOK_SECRET not set. Skipping signature verification.")
        return True

    if not signature_header.startswith("sha1="):
        return False

    expected_digest = signature_header.removeprefix("sha1=")
    computed = hmac.new(
        ENODE_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha1,
    )
    return hmac.compare_digest(computed.hexdigest(), expected_digest)


async def process_enode_event(event: dict, delivery_id: str | None) -> None:
    """Process a single Enode webhook event.

    Handles known meter events by extracting readings and upserting
    meter records. Unknown event types are logged for debugging.
    """
    event_type = event.get("event", "")
    meter_id = event.get("meterId") or event.get("id")

    if event_type in ("user:meter:updated", "user:meter:discovered"):
        # Extract reading data — the payload may contain the full meter object
        # or just the changed fields
        energy = event.get("energyState") or event.get("energy", {})
        power_kw = energy.get("power")
        timestamp = energy.get("lastUpdated") or event.get("createdAt")

        if meter_id and power_kw is not None and timestamp:
            user_id_str = event.get("userId")
            owner_user_id = int(user_id_str) if user_id_str and user_id_str.isdigit() else None
            info = event.get("information") or {}
            save_meter_reading(
                meter_id=meter_id,
                owner_user_id=owner_user_id,
                power_kw=power_kw,
                timestamp=timestamp,
                producer=info.get("brand"),
                model=info.get("model"),
                site_name=info.get("siteName"),
                delivery_id=delivery_id,
                event_type=event_type,
                raw_payload=json.dumps(event, default=str),
            )
            print(f"Webhook: saved reading for meter {meter_id} ({power_kw} kW at {timestamp})")
        elif meter_id:
            print(f"Webhook: incomplete data for meter {meter_id}: power={power_kw}, ts={timestamp}")

    elif event_type == "user:meter:deleted":
        print(f"Webhook: meter {meter_id} deleted by user")

    elif event_type == "enode:webhook:test":
        print(f"Webhook: received test event (delivery={delivery_id})")

    else:
        print(f"Webhook: unknown event type '{event_type}' for meter {meter_id}")
