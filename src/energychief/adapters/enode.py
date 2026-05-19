import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from src.energychief.adapters.base import EnergyDataAdapter
from src.energychief.config import settings

logger = logging.getLogger(__name__)

class EnodeAdapter(EnergyDataAdapter):
    """
    Enode implementation of EnergyDataAdapter.
    Uses OAuth2 client credentials grant.
    """

    def __init__(self, enode_user_id: str, enode_meter_id: Optional[str] = None):
        self.enode_user_id = enode_user_id
        self.enode_meter_id = enode_meter_id
        self.base_url = f"https://enode-api.{settings.ENODE_ENVIRONMENT}.enode.io"
        self.oauth_url = f"https://oauth.{settings.ENODE_ENVIRONMENT}.enode.io/oauth2/token"
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def _ensure_token(self):
        """
        Ensures a valid OAuth2 token is available.
        """
        import time
        if self._token and time.time() < self._token_expires_at - 60:
            return

        logger.info("Fetching new Enode OAuth2 token.")
        client = await self._get_client()
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": settings.ENODE_CLIENT_ID,
            "client_secret": settings.ENODE_CLIENT_SECRET,
        }
        
        response = await client.post(self.oauth_url, data=auth_data)
        response.raise_for_status()
        data = response.json()
        
        self._token = data["access_token"]
        expires_in = data["expires_in"]
        self._token_expires_at = time.time() + expires_in
        logger.debug(f"New token acquired. Expires in {expires_in}s")

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        await self._ensure_token()
        client = await self._get_client()
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        
        url = f"{self.base_url}{path}"
        response = await client.request(method, url, headers=headers, **kwargs)
        
        # Handle token expiration if 401
        if response.status_code == 401:
            logger.warning("Enode token expired, retrying once.")
            self._token = None
            await self._ensure_token()
            headers["Authorization"] = f"Bearer {self._token}"
            response = await client.request(method, url, headers=headers, **kwargs)
            
        return response

    async def refresh_hint(self):
        """
        Triggers Enode refresh hint to speed up data updates.
        """
        if not self.enode_meter_id:
            return
        
        try:
            logger.info(f"Sending refresh hint for meter {self.enode_meter_id}")
            await self._request("POST", f"/meters/{self.enode_meter_id}/refresh-hint")
        except Exception as e:
            logger.warning(f"Failed to send refresh hint: {e}")

    async def get_grid_power_kw(self) -> Optional[float]:
        """
        Returns net power. 
        Note: Enode returns positive=import, negative=export.
        We convert to positive=export, negative=import for our domain.
        """
        if not self.enode_meter_id:
            return None
            
        try:
            response = await self._request("GET", f"/meters/{self.enode_meter_id}")
            response.raise_for_status()
            data = response.json()
            
            # energyState.power: positive = import, negative = export
            power = data.get("energyState", {}).get("power")
            if power is None:
                return None
                
            return -float(power)
        except Exception as e:
            logger.error(f"Error getting grid power from Enode: {e}")
            return None

    async def get_inverter_power_kw(self) -> Optional[float]:
        # Placeholder for future implementation
        return None

    async def get_battery_status(self) -> Optional[Dict[str, Any]]:
        # Placeholder for future implementation
        return None

    async def discover_devices(self) -> Dict[str, Any]:
        """
        Discovers meters associated with the user.
        """
        try:
            response = await self._request("GET", f"/users/{self.enode_user_id}/meters")
            response.raise_for_status()
            meters = response.json()
            
            devices = {"meters": []}
            for m in meters:
                devices["meters"].append({
                    "id": m.get("id"),
                    "type": m.get("type"),
                    "name": m.get("name")
                })
            return devices
        except Exception as e:
            logger.error(f"Error discovering devices in Enode: {e}")
            return {"meters": []}

    async def close(self):
        if self._client:
            await self._client.aclose()
