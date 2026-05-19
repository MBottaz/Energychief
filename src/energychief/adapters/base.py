from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class EnergyDataAdapter(ABC):
    """
    Abstract Base Class for energy data adapters.
    """

    @abstractmethod
    async def get_grid_power_kw(self) -> Optional[float]:
        """
        Returns net power at the connection point.
        > 0 = export to grid, < 0 = import from grid.
        Returns None if not available.
        """
        pass

    @abstractmethod
    async def get_inverter_power_kw(self) -> Optional[float]:
        """
        Returns power produced by the inverter.
        Returns None if not available.
        """
        pass

    @abstractmethod
    async def get_battery_status(self) -> Optional[Dict[str, Any]]:
        """
        Returns battery status.
        Example: {'soc_pct': float, 'power_kw': float}
        Returns None if not present.
        """
        pass

    @abstractmethod
    async def discover_devices(self) -> Dict[str, Any]:
        """
        Discovers Enode devices.
        Returns a dict with meter_id, inverter_id, battery_id, etc.
        """
        pass
