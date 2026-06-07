"""
CLI tool for Enode webhook management.

Usage:
    uv run python -m backend.manage_webhooks list
    uv run python -m backend.manage_webhooks create [--url URL] [--secret SECRET]
    uv run python -m backend.manage_webhooks show <webhook_id>
    uv run python -m backend.manage_webhooks delete <webhook_id>
    uv run python -m backend.manage_webhooks test <webhook_id>

Examples:
    # Create a webhook using WEBHOOK_BASE_URL from .env + auto-generated secret
    uv run python -m backend.manage_webhooks create

    # Create with explicit URL and secret
    uv run python -m backend.manage_webhooks create --url https://example.com/webhooks/enode --secret my-secret-123

    # List all webhooks
    uv run python -m backend.manage_webhooks list

    # Test a webhook
    uv run python -m backend.manage_webhooks test <webhook_id>
"""

import asyncio
import argparse
import secrets
import json

from shared.config import WEBHOOK_BASE_URL, ENODE_WEBHOOK_SECRET
from backend.enode_api import (
    list_webhooks,
    create_webhook,
    get_webhook,
    delete_webhook,
    test_webhook,
)


def _events_default() -> list[str]:
    """Default set of meter-related events."""
    return [
        "user:meter:discovered",
        "user:meter:updated",
        "user:meter:deleted",
    ]


async def cmd_list(args):
    webhooks = await list_webhooks()
    if not webhooks:
        print("No webhooks registered.")
        return

    for wh in webhooks:
        status = "🟢 active" if wh.get("isActive") else "🔴 inactive"
        print(f"  {wh['id']}  {status}  {wh['url']}")
        print(f"      events: {', '.join(wh.get('events', []))}")
        print(f"      last success: {wh.get('lastSuccess', 'never')}")
        print()


async def cmd_create(args):
    url = args.url
    if not url:
        if not WEBHOOK_BASE_URL:
            print(
                "ERROR: No URL provided and WEBHOOK_BASE_URL is not set in .env.\n"
                "  Provide --url or set WEBHOOK_BASE_URL in .env"
            )
            return
        url = f"{WEBHOOK_BASE_URL}/webhooks/enode"

    secret = args.secret or ENODE_WEBHOOK_SECRET
    if not secret:
        secret = secrets.token_hex(32)
        print(f"Auto-generated secret (save this in .env as ENODE_WEBHOOK_SECRET):")
        print(f"  {secret}")
        print()

    events = args.events or _events_default()

    print(f"Creating webhook:")
    print(f"  URL:    {url}")
    print(f"  Events: {', '.join(events)}")
    print()

    try:
        result = await create_webhook(url=url, secret=secret, events=events)
        print(f"✅ Webhook created successfully!")
        print(f"  ID:       {result['id']}")
        print(f"  URL:      {result['url']}")
        print(f"  Active:   {result.get('isActive')}")
        print(f"  Events:   {', '.join(result.get('events', []))}")
        print(f"  Created:  {result.get('createdAt')}")
    except Exception as e:
        print(f"❌ Failed to create webhook: {e}")


async def cmd_show(args):
    try:
        wh = await get_webhook(args.webhook_id)
        print(json.dumps(wh, indent=2, default=str))
    except Exception as e:
        print(f"❌ Failed to get webhook: {e}")


async def cmd_delete(args):
    try:
        await delete_webhook(args.webhook_id)
        print(f"✅ Webhook {args.webhook_id} deleted.")
    except Exception as e:
        print(f"❌ Failed to delete webhook: {e}")


async def cmd_test(args):
    try:
        result = await test_webhook(args.webhook_id)
        status = result.get("status")
        desc = result.get("description", "")
        print(f"Test result: {status} — {desc}")
        if result.get("response"):
            resp = result["response"]
            print(f"  HTTP {resp.get('code')}: {resp.get('body', '(empty)')[:500]}")
    except Exception as e:
        print(f"❌ Test failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Enode webhook subscriptions",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List all registered webhooks")

    p_create = sub.add_parser("create", help="Register a new webhook")
    p_create.add_argument("--url", help="Public HTTPS URL for the webhook endpoint")
    p_create.add_argument("--secret", help="Secret for HMAC signing (auto-generated if omitted)")
    p_create.add_argument("--events", nargs="*", help="Event types (default: meter events)")

    p_show = sub.add_parser("show", help="Show webhook details")
    p_show.add_argument("webhook_id", help="Webhook ID (UUID)")

    p_delete = sub.add_parser("delete", help="Delete a webhook")
    p_delete.add_argument("webhook_id", help="Webhook ID (UUID)")

    p_test = sub.add_parser("test", help="Send a test event to a webhook")
    p_test.add_argument("webhook_id", help="Webhook ID (UUID)")

    args = parser.parse_args()

    cmds = {
        "list": cmd_list,
        "create": cmd_create,
        "show": cmd_show,
        "delete": cmd_delete,
        "test": cmd_test,
    }

    asyncio.run(cmds[args.command](args))


if __name__ == "__main__":
    main()