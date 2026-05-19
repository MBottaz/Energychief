import httpx
import logging
import pandas as pd
from typing import List, Dict, Any
from src.energychief.config import settings

logger = logging.getLogger(__name__)

class WeatherService:
    """
    Service to interact with Open-Meteo API.
    """
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_solar_forecast(self, lat: float, lon: float) -> pd.DataFrame:
        """
        Gets hourly shortwave radiation forecast for the given coordinates.
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "shortwave_radiation",
            "forecast_days": 1
        }
        
        try:
            logger.info(f"Fetching weather forecast for {lat}, {lon}")
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract hourly radiation
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            radiation = hourly.get("shortwave_radiation", [])
            
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(times),
                "radiation": radiation
            })
            return df
        except Exception as e:
            logger.error(f"Error fetching weather forecast: {e}")
            return pd.DataFrame(columns=["timestamp", "radiation"])

    async def close(self):
        await self._client.aclose()
