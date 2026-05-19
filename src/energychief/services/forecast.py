import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.energychief.config import settings

logger = logging.getLogger(__name__)

class ForecastService:
    """
    Service to calculate daily solar production forecasts.
    """

    def __init__(self, weather_service):
        self.weather_service = weather_service

    async def build_daily_forecast(self, lat: float, lon: float, capacity_kwp: float) -> List[Dict[str, Any]]:
        """
        Estimates hourly production based on solar radiation forecast.
        """
        df = await self.weather_service.get_solar_forecast(lat, lon)
        if df.empty:
            return []

        # Default efficiency (performance ratio) is 0.80 as per prompt
        efficiency = 0.80
        
        # Formula: estimated_kw[h] = irradiance[h] / 1000 * capacity_kwp * efficiency
        df['estimated_kw'] = (df['radiation'] / 1000.0) * capacity_kwp * efficiency
        
        # Filter for meaningful hours (> 0.5 kW)
        significant_hours = df[df['estimated_kw'] > 0.5].copy()
        
        forecasts = []
        for _, row in significant_hours.iterrows():
            forecasts.append({
                "timestamp": row['timestamp'],
                "power_kw": float(row['estimated_kw'])
            })
            
        return forecasts
