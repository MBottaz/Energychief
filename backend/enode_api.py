"""
Enode API client — merged from shared/enode_client.py + backend/webhook_manager.py.

All Enode HTTP communication goes through this module:
  - OAuth2 token management
  - User link sessions, meter queries
  - Webhook subscription CRUD
"""

import time

import httpx

from shared.config import ENODE_API_URL

CLIENT_ID = None
CLIENT_SECRET = None
OAUTH_URL = "https://oauth.production.enode.io/oauth2/token"

# Token cache
_token: str | None = None
_token_expires_at: float = 0


def _init_credentials():
    """Lazy-load credentials from env so the module can be imported early."""
    global CLIENT_ID, CLIENT_SECRET
    import os
    if CLIENT_ID is None:
        CLIENT_ID = os.getenv("ENODE_CLIENT_ID")
        CLIENT_SECRET = os.getenv("ENODE_CLIENT_SECRET")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                              AUTH                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


async def get_access_token() -> str:
    global _token, _token_expires_at

    _init_credentials()

    if _token and time.time() < _token_expires_at - 60:  # 60s buffer
        return _token

    async with httpx.AsyncClient() as client:
        response = await client.post(
            OAUTH_URL,
            auth=(CLIENT_ID, CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        data = response.json()

    _token = data["access_token"]
    _token_expires_at = time.time() + data["expires_in"]
    return _token


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Enode-Version": "2024-10-01",
    }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                         USERS & METERS (from enode_client.py)                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


async def create_link_session(user_id: str) -> str:
    """Returns a linkUrl the user must open to connect their meter."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ENODE_API_URL}/users/{user_id}/link",
            headers={
                ** _headers(token),
                "Content-Type": "application/json",
            },
            json={
                "vendorType": "meter",
                "scopes": ["meter:read:data"],
                "language": "it-IT",
            },
        )
        response.raise_for_status()
        return response.json()["linkUrl"]


async def get_meter(meter_id: str) -> dict:
    """Returns full meter object including energyState."""
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENODE_API_URL}/meters/{meter_id}",
            headers=_headers(token),
        )
        response.raise_for_status()
        return response.json()


async def get_user_meters(user_id: str) -> list[dict]:
    """Returns meters associated with a specific user."""
    token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENODE_API_URL}/users/{user_id}/meters",
            headers=_headers(token),
        )
        response.raise_for_status()
        return response.json().get("data", [])


async def get_all_meters() -> list[dict]:
    """
    Fetches all meters across all linked users using the client-wide
    GET /meters endpoint. Handles pagination automatically.
    """
    token = await get_access_token()
    meters = []
    after_cursor = None

    async with httpx.AsyncClient() as client:
        while True:
            params = {"pageSize": 50}
            if after_cursor:
                params["after"] = after_cursor

            response = await client.get(
                f"{ENODE_API_URL}/meters",
                headers=_headers(token),
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            meters.extend(data.get("data", []))

            after_cursor = data.get("pagination", {}).get("after")
            if not after_cursor:
                break

    return meters


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                   WEBHOOK MANAGEMENT (from webhook_manager.py)               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝


async def list_webhooks() -> list[dict]:
    """List all registered webhooks."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENODE_API_URL}/webhooks",
            headers=_headers(token),
            params={"pageSize": 50},
        )
        response.raise_for_status()
        return response.json().get("data", [])


async def create_webhook(
    url: str,
    secret: str,
    events: list[str],
) -> dict:
    """Register a new webhook subscription.

    Args:
        url: Public HTTPS URL (e.g. https://example.com/webhooks/enode)
        secret: Your cryptographically secure secret (used for HMAC signing)
        events: List of event types to subscribe to
                (e.g. ["user:meter:updated", "user:meter:discovered"])
    """
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ENODE_API_URL}/webhooks",
            headers={
                ** _headers(token),
                "Content-Type": "application/json",
            },
            json={
                "url": url,
                "secret": secret,
                "events": events,
                "apiVersion": "2024-10-01",
            },
        )
        response.raise_for_status()
        return response.json()


async def get_webhook(webhook_id: str) -> dict:
    """Get details for a specific webhook."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ENODE_API_URL}/webhooks/{webhook_id}",
            headers=_headers(token),
        )
        response.raise_for_status()
        return response.json()


async def update_webhook(
    webhook_id: str,
    *,
    url: str | None = None,
    secret: str | None = None,
    events: list[str] | None = None,
    active: bool | None = None,
) -> dict:
    """Update fields on an existing webhook subscription."""
    body: dict = {}
    if url is not None:
        body["url"] = url
    if secret is not None:
        body["secret"] = secret
    if events is not None:
        body["events"] = events
    if active is not None:
        body["isActive"] = active

    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{ENODE_API_URL}/webhooks/{webhook_id}",
            headers={
                ** _headers(token),
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        return response.json()


async def delete_webhook(webhook_id: str) -> None:
    """Delete a webhook subscription."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{ENODE_API_URL}/webhooks/{webhook_id}",
            headers=_headers(token),
        )
        response.raise_for_status()


async def test_webhook(webhook_id: str) -> dict:
    """Send a test event to the webhook endpoint."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ENODE_API_URL}/webhooks/{webhook_id}/test",
            headers=_headers(token),
        )
        response.raise_for_status()
        return response.json()